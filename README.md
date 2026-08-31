Task 1
A RTOS is designed to execute tasks within predictable timing constraints, making it suitable for embedded systems such as Formula Student race cars. Unlike general-purpose operating systems, RTOS prioritizes deterministic behavior, ensuring that critical tasks such as reading sensor data, controlling actuators and transmitting telemetry are completed within their required deadlines.
The key components include:
1.	Task scheduling: determines when different tasks execute and ensures important tasks receive CPU time when required. 
2.	Interrupt handling: allows the system to respond quickly to external events such as sensor changes. 
3.	Memory management: ensures efficient usage of limited embedded resources. 
4.	Inter-task communication and synchronization: using mechanisms such as queues, mutexes and semaphores to allow different tasks to communicate safely. 
5.	Device drivers: allows the RTOS to interact with hardware components such as sensors, communication modules and peripherals. 
A comparison table of Zephyr vs rival RTOS’:
Feature	Zephyr RTOS	FreeRTOS	AUTOSAR OS
Ease of learning	Moderate, good documentation	Easy	Difficult
Hardware support	Excellent, especially STM32	Good	Vendor dependent
Built-in features	Extensive networking, logging, drivers and device management	Minimal, requires additional libraries	Extensive automotive features
Community support	Large open-source community backed by the Linux Foundation	Large open-source community	Mainly automotive industry
Automotive suitability	Well suited for embedded automotive projects	Suitable for simpler embedded systems	Best suited for production automotive software
Suitability for Formula Student	Excellent	Good	More complex than necessary
M26 currently uses Zephyr RTOS running on STM32G474RE microcontrollers for both vehicle logic and telemetry. Based on the current requirements and the existing software architecture, I believe Zephyr should continue to be used for M27.
The reasons are as follows:
1.	The current system is already capable of handling vehicle logic and telemetry tasks successfully. Since there is no clear technical limitation with Zephyr, replacing the RTOS would introduce unnecessary development effort and risk.
2.	Changing the RTOS would involve adapting existing drivers, modifying task scheduling behavior, rewriting parts of the software stack and requiring the team to become familiar with a new development environment. For a student team with limited development time, this effort may not provide enough benefit.
3.	Zephyr provides built-in support for multithreading, networking, logging, power management and various device drivers. It also has strong STM32 support, allowing developers to rely on existing drivers and documentation instead of maintaining custom implementations.
4.	Formula Student teams experience frequent member turnover as students graduate and new members join. Therefore, having an RTOS with good documentation, active community support and a relatively easy learning curve is important. Continuing with Zephyr allows future members to improve the vehicle rather than spending significant time learning a completely new platform.
Overall, I recommend continuing with Zephyr for M27. It already satisfies the team's technical requirements, provides strong STM32 support, and offers an extensive set of built-in features that reduce development effort. Most importantly, it allows the team to build on an existing and proven software platform instead of investing valuable time in migrating to a different RTOS. Unless future versions of the vehicle require automotive-grade functional safety certification or capabilities that Zephyr cannot provide, the benefits of switching to FreeRTOS or AUTOSAR OS do not outweigh the additional cost, risk and engineering effort involved
Task 2
To design a live telemetry system for M27, my main priority would be creating a reliable pipeline that can transfer vehicle data to a public dashboard while maintaining low latency and keeping the system practical for a Formula Student team to maintain.
My approach would be: Sensors > STM32 + Zephyr > CAN Bus > Telemetry Node > 5 GHz Wi-Fi > Trackside Ground Station > Database > Dashboard + Livestream Overlay.
This is further detailed in the table below:
Layer	Proposed Technology	Reasoning
Vehicle RTOS	Zephyr	Existing software platform already used in M26
Vehicle Communication	CAN Bus	Reliable, industry-standard communication between ECUs
Wireless Communication	5 GHz Wi-Fi	High bandwidth and low latency for telemetry and video
Telemetry Decoding	python-can and cantools	Converts CAN messages into readable telemetry 
Database	PostgreSQL (with TimescaleDB if required)	Reliable storage for live and historical telemetry
Dashboard	Grafana	Real-time visualization with strong PostgreSQL integration
Data Analytics	Python, Pandas, Jupyter Notebook	ETL and post-session performance analysis
Video Streaming	OBS Studio	Combines live telemetry overlays with video for public streaming
The reasoning behind this architecture is as follows
1.	Vehicle data collection: STM32 running Zephyr could continue handling vehicle logic and collect data from sensors. Communication between vehicle components would occur through CAN Bus. And a dedicated telemetry node would listen to required CAN messages such as vehicle speed, etc., separating telemetry from operations.
2.	Wireless communication: I would use a 5 GHz wifi because telemetry data itself requires low bandwidth. Wi-Fi provides lower latency and higher throughput compared with alternatives such as LoRa or Bluetooth.
3.	Trackside data processing: a ground station computer would receive and process incoming telemetry. The telemetry receiver would decode CAN messages using tools such as python-can and cantools, converting raw CAN frames into readable values. The processed data would then be stored in PostgreSQL. If the telemetry volume increases in future seasons, TimescaleDB could be used on top of PostgreSQL because it is designed for time-series data.
4.	For visualization, it is best to use Grafana to create a live telemetry dashboard because it is designed for real-time metrics, integrates well with PostgreSQL, and allows engineers and spectators to view live vehicle performance data. It can also be provided to OBS to overlay information onto a livestream as well.
5.	Post-session analytics: I would use Python, Pandas and Jupyter Notebook to perform ETL and analyze historical telemetry. The processed results could then be stored back into PostgreSQL so that future dashboards and analysis tools can access enriched data. Apache Airflow could become useful eventually if the team requires an automated reporting pipeline or large-scale data processing.
To sum up, my proposed architecture prioritizes reliability, simplicity and maintainability while making use of technologies that are widely adopted and well supported. By keeping the live telemetry pipeline lightweight and performing more advanced analytics after each session, the team can deliver a responsive public dashboard without compromising the performance of the vehicle or increasing unnecessary system complexity. This approach also provides a solid foundation that can be expanded in future seasons as new telemetry requirements emerge.
Task 3
I noted the following and my deduction as follows:
1.	When the APPS is unplugged, the driver presses pedal > No APPS signal > Fault detected > Torque gets set to 0 > motor disabled, therefore the motor should never accelerate. 
2.	The motor briefly ramps up, which means the ECU doesn’t detect the fault immediately. Instead, the sensor gets unplugged > old throttle value still exists > controller still commands torque > motor speeds up > fault detected > shutdown or the control task gets delayed > fault handling delayed > old output remains active > motor ramps up > fault trips.
3.	Since the system previously passed the same inspection test during university testing, the hardware, APPS sensor and wiring are less likely to be the root cause. Although they cannot be completely ruled out, the evidence suggests the recent software change is a more likely explanation.
4.	Lastly, since the only reported software change was increasing the logging task from 10 Hz to 100 Hz, my initial hypothesis is that the additional logging load affected the scheduling behavior of the RTOS. If the logging task has a high priority or performs blocking operations, it may delay the execution of safety-critical control tasks responsible for monitoring the APPS sensor. As a result, the ECU may continue using the last valid accelerator value for a short period before detecting the sensor fault and shutting the motor down.
To mitigate at competition with time constraints I’d perform the following quick fixes:
1.	Revert logging back to 10 Hz. 
2.	Repeat APPS inspection test. 
3.	Compare CPU usage. 
4.	Check task priorities. 
5.	Disable unnecessary logging temporarily. 
6.	Add timestamps around safety task.
Long-term improvements would be:
1.	Separate safety tasks along and never block logging. Instead of read the sensor and write it on SD card, we could read the sensor > put the data in a queue and then a logging task writes it later.
2.	Deadline monitoring.
3.	Perform unit tests on APPS in simulation.
4.	Measure CPU utilization.
 Task 4
Please download the ‘task 4 analysis.ipynb’ file from this repo and open in and run it on Google Colab or Jupyter Notebook or locally on your code editor too.
Task 5
For this task I decided not to just pick one of the three suggested ideas (race visualizer, season drop-off, fuel load vs lap time) and treat it as a single feature. Instead, I built a tool where the fuel-load analysis feeds directly into the season drop-off analysis, since a driver's pace early in a stint (or early in a season) can't be fairly compared to their pace later on without first correcting for how much lighter the car has gotten. So my pipeline is:
raw lap times > fuel-corrected pace > per-stint tyre degradation fit > aggregated across a season > is this driver's tyre management/pace trending up or down?
with a bonus telemetry-overlay mode added on top since FastF1 makes it very simple and it's a nice visual to include.
My reasoning behind the pipeline is as follows:
1.	Fuel correction: F1 cars get faster over a stint partly because tyres are more consistent early on, but also simply because they're burning off fuel. A fully-fuelled car is meaningfully heavier than a near-empty one. If this isn't accounted for, degradation slopes look artificially small (fuel burn partially cancels out tyre fall-off in the raw numbers), and comparisons across different points in a fuel curve aren't apples-to-apples. I modelled fuel as burning off linearly from a starting load (110kg, an approximation of a modern F1 starting fuel load) down to empty across the race distance, with each kg costing roughly 0.03 seconds of lap time. Neither of these numbers is official F1 data since teams don't publish this. 0.03s/kg is a commonly cited ballpark figure in F1 fan-analytics, so I exposed both as tunable constants at the top of the script rather than hardcoding them as if they were precise.
2.	Degradation fit: within each stint, I regressed fuel-corrected lap time against tyre life (laps run on that set of tyres) using a simple linear fit. Real degradation is often mildly non-linear (a "cliff" near the end of a long stint), but a single slope number is easy to compare across stints, races and drivers, which was the point of the exercise. I report R² alongside every fit so a poor linear fit is visible rather than hidden.
3.	Cleaning laps before fitting: pit in/out laps and laps run under anything other than green-flag conditions (safety car, VSC, red flag) are dropped before fitting, since both run at a pace that has nothing to do with tyre wear and would otherwise distort the regression.
4.	Season drop-off: for every round in a season, I refit the degradation model and also compute a competitive gap: the driver's median fuel-corrected lap time minus the fastest fuel-corrected lap set by anyone that race. Plotting both trends separately matters because they represent two different problems: getting worse at managing tyres (rising degradation slope) versus simply losing outright pace relative to the field (rising competitive gap). A driver could have one problem without the other, and lumping them together would hide that.
I validated the code in a way that didn't rely on having live access to F1's timing servers during development:
1.	I checked every FastF1 function and method the script calls (get_session, get_event_schedule, Cache.enable_cache, plotting.setup_mpl, plotting.get_driver_color, plotting.get_compound_color, Laps.pick_drivers, Lap.get_car_data, Telemetry.add_distance) against a locally installed copy of the fastf1 package to confirm each one exists with the exact signature I used.
2.	I tested the fuel-correction and regression logic against synthetic lap data with a known, injected degradation slope and fresh-tyre pace. The fit recovered the true slope (0.08 s/lap) to within 0.002 s/lap and the true pace (90.0s) to within 0.06s, with R² above 0.99.
3.	I ran the full plotting code path against synthetic multi-stint data to confirm there were no runtime errors before testing against real data.
Once I had access to a machine with internet, I ran the tool against real 2025 season data (Silverstone) and confirmed all three modes work end to end.
Steps to run:
1.	Clone the repo and navigate into it.
2.	Create a virtual environment: python -m venv .venv, then activate it (.venv\Scripts\activate on Windows, source .venv/bin/activate on Mac/Linux).
3.	Install dependencies: pip install -r requirements.txt.
4.	Run one of the three modes: 
•	Single-race stint degradation: python task5.py stint --year 2025 --event Silverstone --session R --driver PIA
•	Season-long drop-off trend: python task5.py season --year 2025 --driver PIA
•	Telemetry comparison: python task5.py compare --year 2025 --event Silverstone --session Q --drivers PIA NOR
5.	The first run downloads and caches session data locally (a ff1_cache folder gets created automatically), so it can take a little while. Subsequent runs on the same session are much faster.
6.	Each command accepts an optional --save path/to/file.png flag to save the plot instead of just displaying it.

Results
<img width="1000" height="600" alt="Figure_1" src="https://github.com/user-attachments/assets/6bcc1808-a7dc-44f3-9c57-a370d9f808a7" />
<img width="508" height="423" alt="Figure_2" src="https://github.com/user-attachments/assets/714818b3-0519-427f-a0f4-6128639cee8d" />
