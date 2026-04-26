# LiveKit Voice AI Deployment Guide

This guide details the infrastructure and system-level requirements to run the modernized Voice AI agent at scale, matching the performance of LiveKit Cloud.

## 1. Hardware Capacity Planning

Voice AI agents are compute-intensive. Capacity is primarily bound by CPU and Memory for the Python workers.

| Concurrent Calls | Agent Worker Pool (vCPU / RAM) | LiveKit SFU (vCPU / RAM) |
| :--- | :--- | :--- |
| **10 - 25** | 4 vCPU / 8 GB | 2 vCPU / 4 GB |
| **50** | 8 - 12 vCPU / 24 GB | 2 vCPU / 4 GB |
| **500** | 100 - 150 vCPU / 400 GB | 4 vCPU / 8 GB |
| **1,000** | 200 - 300 vCPU / 800 GB | 8 vCPU / 16 GB |

**Recommended Instances:** Compute-optimized types like AWS `c7g`, GCP `c3`, or Azure `Fsv2`.

---

## 2. Ubuntu Server / Kernel Tuning

To prevent packet loss and handle thousands of concurrent UDP streams, apply these sysctl optimizations:

```bash
# Increase UDP buffers
sudo sysctl -w net.core.rmem_max=2500000
sudo sysctl -w net.core.wmem_max=2500000

# Increase open file limits
echo "* soft nofile 65535" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65535" | sudo tee -a /etc/security/limits.conf

# Enable BBR Congestion Control (for smoother audio over lossy networks)
echo "net.core.default_qdisc=fq" | sudo tee -a /etc/sysctl.conf
echo "net.ipv4.tcp_congestion_control=bbr" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

---

## 3. Networking Best Practices

### Host Networking
If running via Docker, **absolute requirement:** use `--net=host`.
Docker's bridge network adds NAT overhead that increases jitter and CPU usage for WebRTC audio packets.

### Co-location
Deploy your Python Agent workers in the same datacenter (VPC) as your LiveKit SFU.
*   **Target:** Internal network latency between SFU and Agent should be **< 2ms**.

### Firewall / Ports
Open the following ports on your host:
*   `443/tcp`: HTTPS/WSS (API & Signaling)
*   `7881/tcp`: LiveKit internal signaling
*   `443/udp`: WebRTC Media (primary)
*   `50000-60000/udp`: WebRTC Media (fallback range)

---

## 4. Scaling Strategy

1.  **Vertical Scaling:** Start with 4-8 vCPU nodes for agent workers.
2.  **Horizontal Scaling:** Use a Load Balancer in front of multiple LiveKit SFU nodes (Redis-backed multinode setup).
3.  **Worker Management:** LiveKit Agents automatically handle job distribution. Scale your worker nodes when average CPU utilization across the pool exceeds **50%**.
