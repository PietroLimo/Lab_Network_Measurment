from pythonping import ping
import statistics

def ping_with_stats(target: str, count: int = 4, timeout: int = 2):
    print(f"\n--- Pinging {target} with {count} packets ---")

    response = ping(target, count=count, timeout=timeout)

    rtts = []

    for i, resp in enumerate(response, start=1):
        if resp.success:
            rtt = resp.time_elapsed_ms
            rtts.append(rtt)
            print(f"Packet {i}: RTT = {rtt:.2f} ms")
        else:
            print(f"Packet {i}: Request timed out")

    sent = response.stats_packets_sent
    received = response.stats_packets_returned
    loss = ((sent - received) / sent) * 100 if sent > 0 else 0

    print("\n--- Statistics ---")
    print(f"Packets: sent={sent}, received={received}, loss={loss:.2f}%")

    if rtts:
        print(f"RTT min     = {min(rtts):.2f} ms")
        print(f"RTT max     = {max(rtts):.2f} ms")
        print(f"RTT average = {statistics.mean(rtts):.2f} ms")
        print(f"RTT std dev = {statistics.pstdev(rtts):.2f} ms")
    else:
        print("No RTT samples available (100% packet loss)")

    return {
        "sent": sent,
        "received": received,
        "loss": loss,
        "rtts": rtts
    }


if __name__ == "__main__":
    # Input destinazione
    target = input("Inserisci la destinazione (IP o hostname): ").strip()
    if not target:
        print("Errore: destinazione non valida.")
        exit(1)

    # Input count con default
    count_input = input("Inserisci il numero di pacchetti (default 4): ").strip()

    try:
        count = int(count_input) if count_input else 4
        if count <= 0:
            raise ValueError
    except ValueError:
        print("Numero di pacchetti non valido.")
        exit(1)

    ping_with_stats(target, count)