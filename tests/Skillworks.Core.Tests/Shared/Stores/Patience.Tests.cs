using Skillworks.Core.Shared.Stores;

namespace Skillworks.Core.Tests.Shared.Stores;

public sealed class PatienceTests
{
    // The wait HttpClient keeps of its own, named here so raising the ceiling past it fails.
    private static readonly TimeSpan TheClientsOwnWait = TimeSpan.FromSeconds(100);

    [Theory]
    [InlineData(0)]
    [InlineData(-5)]
    public void Waits_a_second_at_least_however_little_a_request_is_given(int seconds) =>
        Assert.Equal(TimeSpan.FromSeconds(1), Patience.PerRequest(seconds).Length);

    [Theory]
    [InlineData(0)]
    [InlineData(-5)]
    public void Waits_a_second_at_least_however_little_a_read_is_given(int seconds) =>
        Assert.Equal(TimeSpan.FromSeconds(1), Patience.PerRead(seconds).Length);

    [Fact]
    public void Waits_the_seconds_a_request_is_given() =>
        Assert.Equal(TimeSpan.FromSeconds(42), Patience.PerRequest(42).Length);

    [Fact]
    public void Holds_a_request_inside_the_wait_the_client_measures_on_the_machines_clock() =>
        Assert.True(Patience.PerRequest(1000).Length < TheClientsOwnWait);

    [Fact]
    public void Lets_a_whole_read_outlast_that_wait_because_no_read_ever_meets_it() =>
        Assert.Equal(TimeSpan.FromSeconds(1000), Patience.PerRead(1000).Length);

    [Fact]
    public void Writes_one_sentence_naming_what_fell_short_and_what_the_wait_covered() =>
        Assert.Equal(
            "http://localhost:3100/ did not answer inside the 5 seconds Studio waits for one request.",
            Patience.PerRequest(5).RanOut("http://localhost:3100/", Patience.OneRequest));
}
