from pythonping import ping
import statistics
from colorama import Fore, Style, init

init(autoreset=True)

def run_measurement(target, count=50, timeout=2):
    print(f"\n--- Pinging {target} ({count} packets) ---")

    response = ping(target, count=count, timeout=timeout)

    rtts = []

    # Stampa ogni pacchetto
    for i, resp in enumerate(response, start=1):
        if resp.success:
            rtt = resp.time_elapsed_ms
            rtts.append(rtt)
            print(f"Packet {i}: Reply from {target} "
                  f"time={rtt:.2f} ms")
        else:
            print(Fore.RED +
                  f"Packet {i}: Request timed out" + Style.RESET_ALL)

    sent = response.stats_packets_sent
    received = response.stats_packets_returned
    loss = ((sent - received) / sent) * 100

    print("\n--- Statistics ---")
    print(f"Packets: sent={sent}, received={received}, loss={loss:.2f}%")

    if rtts:
        print(Fore.CYAN    + f"RTT min   = {min(rtts):.2f} ms" + Style.RESET_ALL)
        print(Fore.MAGENTA + f"RTT max   = {max(rtts):.2f} ms" + Style.RESET_ALL)
        print(Fore.GREEN   + f"RTT mean  = {statistics.mean(rtts):.2f} ms" + Style.RESET_ALL)
        print(Fore.YELLOW  + f"RTT std   = {statistics.pstdev(rtts):.2f} ms" + Style.RESET_ALL)
    else:
        print(Fore.RED + "No RTT samples available (100% packet loss)" + Style.RESET_ALL)

    return {
        "sent": sent,
        "received": received,
        "loss": loss,
        "rtts": rtts
    }

if __name__ == "__main__":
    target_host = "8.8.8.8"
    run_measurement(target_host, count=50, timeout=2)