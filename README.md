# PLC-MQTT Communication Gateway using USR-W610

This project demonstrates a robust communication link between a PLC and a local monitoring station. By utilizing the USR-W610 in a local WiFi environment, data is retrieved from PLC registers via Modbus RTU and served locally via Modbus TCP. This setup is designed for high-security industrial environments where external internet access is restricted.

This project can be configured to be used through a wifi with no internet access in which case only devices connected to the same wifi as the USR-W610 can access the data.

Or the data can be accessed through A Mqtt Broker through the Internet .

The python code for a dashboard for the no internet wifi case is attached,and for the mqtt case a html file is attached.

Read the Sop-Usr for further clarifications.

Key Features:

Dual-Protocol Support: Configured for both Modbus TCP (for local master devices) and MQTT (for cloud/dashboard integration).  
Reliable Hardware Interface: Utilizes RS485 (COM2) wiring for industrial-grade serial communication.  

Custom Heartbeat Function: Implemented a polling mechanism to retrieve register data (e.g., register D100) at 3-second intervals.  
Static IP Configuration: Configured via WAN static mode to ensure persistent connections even after device reboots.  

Technical Stack:

Hardware: PLC, USR-W610 (RS485 to WiFi/Ethernet Converter).  
Protocols: Modbus RTU, Modbus TCP, MQTT.  
Software: Modbus Poll (Master simulator), HiveMQ (MQTT Broker), Python (Dashboard).
Setup Instructions


Wiring: Connect PLC COM2 (+) and (-) to USR-W610 A and B ports.  
USR-W610 Config: Access the web UI at 10.10.100.254 and set the device to STA Mode.  
Network: Configure Static IP, Gateway, and DNS (8.8.8.8) to match your local industrial network.  

MQTT Bridge: Enable Transparent Mode and configure the HiveMQ server address at port 1883.
