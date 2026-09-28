using System.Net;
using System.Text;
using System.Web;

namespace Skillworks.Core.Tests.Shared.Harness.StandIns;

// Stands in for an events store that answers nothing until a test lets it, which a running Loki cannot be made to do.
public sealed class StallingEventsStore : HttpMessageHandler
{
    private const string NothingFound = """{"status":"success","data":{"resultType":"vector","result":[]}}""";

    private readonly Lock _gate = new();
    private readonly List<string> _queries = [];
    private readonly List<(int Reads, TaskCompletionSource Reached)> _waits = [];
    private readonly TaskCompletionSource _letGo = new(TaskCreationOptions.RunContinuationsAsynchronously);

    private int _atOnce;
    private int _mostAtOnce;

    // A test waits for this before it moves the Clock, so no test moves it on a wait instead.
    public Task Asked => AskedFor(1);

    public IReadOnlyList<string> Queries
    {
        get
        {
            lock (_gate)
            {
                return [.. _queries];
            }
        }
    }

    public int MostAtOnce
    {
        get
        {
            lock (_gate)
            {
                return _mostAtOnce;
            }
        }
    }

    public Task AskedFor(int reads)
    {
        lock (_gate)
        {
            if (_queries.Count >= reads)
            {
                return Task.CompletedTask;
            }

            var reached = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);

            _waits.Add((reads, reached));

            return reached.Task;
        }
    }

    public void LetGo() => _letGo.TrySetResult();

    protected override async Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request,
        CancellationToken cancellationToken)
    {
        lock (_gate)
        {
            _queries.Add(HttpUtility.ParseQueryString(request.RequestUri?.Query ?? "")["query"] ?? "");
            _atOnce++;
            _mostAtOnce = Math.Max(_mostAtOnce, _atOnce);

            foreach (var wait in _waits.Where(wait => wait.Reads <= _queries.Count))
            {
                wait.Reached.TrySetResult();
            }
        }

        try
        {
            // Awaiting the winner rethrows what a real send given up on throws, which a finished WhenAny would swallow.
            await await Task.WhenAny(_letGo.Task, Never.Answers(cancellationToken));
        }
        finally
        {
            lock (_gate)
            {
                _atOnce--;
            }
        }

        return new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent(NothingFound, Encoding.UTF8, "application/json"),
        };
    }
}
