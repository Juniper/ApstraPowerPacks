# Cos Auto Tuner

AI workloads place unique stresses on the network. Packet loss has a particularly deleterious effect.
To maximize throughput and minimize packet loss, Ethernet uses the DCQCN congestion management protocol, but DCQCN introduces significant operational complexity for human operators. Using Apstra's custom Telemetry Collectors, and Configlets, our automation takes this new challenge in stride, automatically optimizing for throughput and the “right amount” of packet loss.

This project uses Apstra to monitor the network and deploy changes into the network to tune it appropriately.

## Requirements

- Apstra 4.2.0 or above
- Apstra should have the custom probes found in the Interface_Queue_Drops, ECN_Marked_Packets and PFC_Counter instantiated and enabled
- Terraform needs to be installed
- python 3 or above

## Background 
- What is DCQCN? https://www.juniper.net/documentation/us/en/software/junos/traffic-mgmt-qfx/topics/topic-map/cos-qfx-series-DCQCN.html
- Cloud Field Day Presentation https://www.youtube.com/watch?v=87LYgLSr5Js

## Usage

1. pip3 install -r ./requirements.txt
2. copy setup.yaml.template to setup.yaml. Fill in the values as appropriate
3. Fill out apstra_snow_setup.sh
4. % source apstra_snow_setup.sh
5. % python ecn_monitor.py --init 
6. % python ecn_monitor.py 
7. To reset the automation: python ecn_monitor.py --restore-original

## ToDo
1. Containerize



