using System.Collections.Concurrent;
using System.Net;
using System.Net.Sockets;
using System.Text;

namespace Skillworks.Core.Tests.Shared.Harness.StandIns;

// Only a real socket shows the connections Studio opens.
public sealed class SocketEventsStore : IDisposable
{
    private const string NothingFound = """{"status":"success","data":{"resultType":"vector","result":[]}}""";

    private readonly TcpListener _listener = new(IPAddress.Loopback, 0);
    private readonly ConcurrentBag<TcpClient> _accepted = [];

    public SocketEventsStore()
    {
        _listener.Start();
        _ = AcceptAsync();
    }

    public Uri Address => new($"http://127.0.0.1:{((IPEndPoint)_listener.LocalEndpoint).Port}/");

    public int Connections => _accepted.Count;

    private async Task AcceptAsync()
    {
        try
        {
            while (true)
            {
                var client = await _listener.AcceptTcpClientAsync();

                _accepted.Add(client);
                _ = AnswerAsync(client);
            }
        }
        catch (Exception stopped) when (stopped is SocketException or ObjectDisposedException)
        {
        }
    }

    // Held open like a real store's, so a pooling client would reuse it.
    private static async Task AnswerAsync(TcpClient client)
    {
        try
        {
            var stream = client.GetStream();
            using var request = new StreamReader(stream, Encoding.ASCII, leaveOpen: true);

            while (await request.ReadLineAsync() is { } line)
            {
                // Studio only ever asks with a GET, so a blank line ends the request.
                if (line.Length > 0)
                {
                    continue;
                }

                var body = Encoding.UTF8.GetBytes(NothingFound);
                var head = Encoding.ASCII.GetBytes(
                    $"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {body.Length}\r\n\r\n");

                await stream.WriteAsync(head);
                await stream.WriteAsync(body);
            }
        }
        catch (Exception stopped) when (stopped is IOException or ObjectDisposedException)
        {
        }
    }

    public void Dispose()
    {
        _listener.Stop();

        foreach (var client in _accepted)
        {
            client.Dispose();
        }
    }
}
