## Task 1

### Overview

An RTOS is designed to execute tasks within predictable timing constraints, making it suitable for embedded systems such as Formula Student race cars. Unlike general-purpose operating systems, an RTOS prioritizes deterministic behavior, ensuring critical tasks such as reading sensor data, controlling actuators, and transmitting telemetry are completed within their required deadlines.

**Key components:**

- **Task scheduling**: determines when different tasks execute and ensures important tasks receive CPU time when required.
- **Interrupt handling**: allows the system to respond quickly to external events such as sensor changes.
- **Memory management**: ensures efficient usage of limited embedded resources.
- **Inter-task communication and synchronization**: mechanisms such as queues, mutexes, and semaphores that allow different tasks to communicate safely.
- **Device drivers**: allow the RTOS to interact with hardware components such as sensors, communication modules, and peripherals.

### RTOS Comparison

| Feature | Zephyr RTOS | FreeRTOS | AUTOSAR OS |
|---|---|---|---|
| Ease of learning | Moderate, good documentation | Easy | Difficult |
| Hardware support | Excellent, especially STM32 | Good | Vendor dependent |
| Built-in features | Extensive networking, logging, drivers and device management | Minimal, requires additional libraries | Extensive automotive features |
| Community support | Large open-source community backed by the Linux Foundation | Large open-source community | Mainly automotive industry |
| Automotive suitability | Well suited for embedded automotive projects | Suitable for simpler embedded systems | Best suited for production automotive software |
| Suitability for Formula Student | Excellent | Good | More complex than necessary |

`M26` currently uses `Zephyr RTOS` running on `STM32G474RE` microcontrollers for both vehicle logic and telemetry. Based on the current requirements and existing software architecture, **Zephyr should continue to be used for M27**.

Reasoning:

1. The current system already handles vehicle logic and telemetry tasks successfully. With no clear technical limitation in Zephyr, replacing the RTOS would introduce unnecessary development effort and risk.
2. Changing the RTOS would involve adapting existing drivers, modifying task scheduling behavior, rewriting parts of the software stack, and requiring the team to become familiar with a new development environment. For a student team with limited development time, this effort may not provide enough benefit.
3. Zephyr provides built-in support for multithreading, networking, logging, power management, and various device drivers, with strong STM32 support that lets developers rely on existing drivers and documentation instead of maintaining custom implementations.
4. Formula Student teams experience frequent member turnover as students graduate and new members join, so an RTOS with good documentation, active community support, and a relatively easy learning curve matters. Continuing with Zephyr lets future members improve the vehicle rather than spend significant time learning a new platform.

Overall, Zephyr already satisfies the team's technical requirements, provides strong STM32 support, and offers an extensive set of built-in features that reduce development effort. It allows the team to build on an existing, proven software platform instead of investing valuable time migrating to a different RTOS. Unless future vehicle versions require automotive-grade functional safety certification or capabilities Zephyr can't provide, the benefits of switching to FreeRTOS or AUTOSAR OS don't outweigh the additional cost, risk, and engineering effort involved.

---

## Task 2

### Overview

The main priority for a live telemetry system for M27 is a reliable pipeline that transfers vehicle data to a public dashboard while maintaining low latency and staying practical for a Formula Student team to maintain.

**Proposed architecture:**

`Sensors` > `STM32 + Zephyr` > `CAN Bus` > `Telemetry Node` > `5 GHz Wi-Fi` > `Trackside Ground Station` > `Database` > `Dashboard + Livestream Overlay`

### Technology Stack

| Layer | Proposed Technology | Reasoning |
|---|---|---|
| Vehicle RTOS | Zephyr | Existing software platform already used in M26 |
| Vehicle Communication | CAN Bus | Reliable, industry-standard communication between ECUs |
| Wireless Communication | 5 GHz Wi-Fi | High bandwidth and low latency for telemetry and video |
| Telemetry Decoding | `python-can` and `cantools` | Converts CAN messages into readable telemetry |
| Database | PostgreSQL (with TimescaleDB if required) | Reliable storage for live and historical telemetry |
| Dashboard | Grafana | Real-time visualization with strong PostgreSQL integration |
| Data Analytics | Python, Pandas, Jupyter Notebook | ETL and post-session performance analysis |
| Video Streaming | OBS Studio | Combines live telemetry overlays with video for public streaming |

### Design Reasoning

1. **Vehicle data collection**: STM32 running Zephyr continues to handle vehicle logic and collect sensor data, with communication between vehicle components over CAN Bus. A dedicated telemetry node listens to required CAN messages (vehicle speed, etc.), separating telemetry from operations.
2. **Wireless communication**: 5 GHz Wi-Fi is used because telemetry data itself requires low bandwidth, and Wi-Fi provides lower latency and higher throughput than alternatives like LoRa or Bluetooth.
3. **Trackside data processing**: a ground station computer receives and processes incoming telemetry. The receiver decodes CAN messages using `python-can` and `cantools`, converting raw CAN frames into readable values, which are then stored in PostgreSQL. If telemetry volume increases in future seasons, `TimescaleDB` could be layered on top since it's designed for time-series data.
4. **Visualization**: Grafana is used for the live telemetry dashboard since it's designed for real-time metrics, integrates well with PostgreSQL, and lets both engineers and spectators view live vehicle performance data. It can also feed OBS to overlay information onto a livestream.
5. **Post-session analytics**: Python, Pandas, and Jupyter Notebook handle ETL and analysis of historical telemetry. Processed results feed back into PostgreSQL so future dashboards and analysis tools can access enriched data. Apache Airflow could become useful if the team eventually needs an automated reporting pipeline or large-scale data processing.

This architecture prioritizes reliability, simplicity, and maintainability using widely adopted, well-supported technologies. Keeping the live pipeline lightweight and performing more advanced analytics after each session lets the team deliver a responsive public dashboard without compromising vehicle performance or adding unnecessary system complexity, while providing a foundation that can expand in future seasons.

---

## Task 3

### Observations & Deduction

1. When the APPS is unplugged and the driver presses the pedal: `no APPS signal` > `fault detected` > `torque set to 0` > `motor disabled`, the motor should therefore never accelerate.
2. The motor briefly ramps up, meaning the ECU doesn't detect the fault immediately. Most likely: `sensor unplugged` > `old throttle value still held` > `controller still commands torque` > `motor speeds up` > `fault detected` > `shutdown` — or the control task itself is delayed, so fault handling is delayed, the old output remains active, the motor ramps up, and the fault trips afterward.
3. Since the system previously passed the same inspection test during university testing, the hardware, APPS sensor, and wiring are less likely to be the root cause. They can't be fully ruled out, but the evidence points more strongly to the recent software change.
4. The only reported software change was increasing the logging task from `10 Hz` to `100 Hz`. Initial hypothesis: the additional logging load affected RTOS scheduling behavior. If the logging task has high priority or performs blocking operations, it may delay execution of the safety-critical control task responsible for monitoring the APPS sensor — meaning the ECU continues using the last valid accelerator value briefly before detecting the sensor fault and shutting the motor down.

### Quick Fixes 

- Revert logging back to 10 Hz.
- Repeat APPS inspection test.
- Compare CPU usage.
- Check task priorities.
- Disable unnecessary logging temporarily.
- Add timestamps around the safety task.

### Long-Term Improvements

- Separate safety tasks so they never block logging, e.g. read the sensor, place data in a queue, and let a separate logging task write it later instead of reading and writing to SD card in the same path.
- Add deadline monitoring.
- Perform unit tests on APPS in simulation.
- Measure CPU utilization.

---

## Task 4

Download `task 4 analysis.ipynb` from this repo and open/run it in Google Colab, Jupyter Notebook, or locally in your code editor of choice.

---

## Task 5

### Overview

Rather than treating the three suggested ideas (race visualizer, season drop-off, fuel load vs lap time) as separate options, this tool chains them: fuel-load correction feeds directly into a tyre degradation fit, which is then aggregated across a season to answer whether a driver's tyre management and pace are trending up or down.

**Pipeline:**

`raw lap times` > `fuel-corrected pace` > `per-stint tyre degradation fit` > `aggregated across a season` > `is this driver's tyre management/pace trending up or down?`

A bonus telemetry-overlay mode is included on top of this, since `FastF1` makes it simple and it's a useful visual to include.

### Design Reasoning

- **Fuel correction**: F1 cars get faster over a stint partly from tyres settling in, but also simply from burning off fuel. A fully-fuelled car is meaningfully heavier than a near-empty one, and without correcting for this, degradation slopes look artificially small. Fuel is modelled as burning off linearly from a starting load (`110kg`, an approximation of a modern F1 starting fuel load) to empty across the race distance, with each kg costing roughly `0.03s` of lap time. Neither number is official F1 data since teams don't publish this; `0.03s/kg` is a commonly cited ballpark figure in F1 fan-analytics, so both are exposed as tunable constants at the top of the script rather than hardcoded as precise values.
- **Degradation fit**: within each stint, fuel-corrected lap time is regressed against tyre life (laps run on that set of tyres) using a simple linear fit. Real degradation is often mildly non-linear (a "cliff" near the end of a long stint), but a single slope number is easy to compare across stints, races, and drivers. `R²` is reported alongside every fit so a poor linear fit is visible rather than hidden.
- **Lap cleaning**: pit in/out laps and laps run under anything other than green-flag conditions (safety car, VSC, red flag) are dropped before fitting, since both run at a pace unrelated to tyre wear and would otherwise distort the regression.
- **Season drop-off**: for every round in a season, the model is refit and a competitive gap is also computed: the driver's median fuel-corrected lap time minus the fastest fuel-corrected lap set by anyone that race. Plotting both trends separately matters, since a driver can get worse at managing tyres (rising degradation slope) without losing outright pace relative to the field (rising competitive gap), or vice versa.

### Validation

Validated without relying on live access to F1's timing servers during development:

- Checked every `FastF1` function and method the script calls (`get_session`, `get_event_schedule`, `Cache.enable_cache`, `plotting.setup_mpl`, `plotting.get_driver_color`, `plotting.get_compound_color`, `Laps.pick_drivers`, `Lap.get_car_data`, `Telemetry.add_distance`) against a locally installed copy of the `fastf1` package to confirm each exists with the exact signature used.
- Tested the fuel-correction and regression logic against synthetic lap data with a known, injected degradation slope and fresh-tyre pace. The fit recovered the true slope (`0.08 s/lap`) to within `0.002 s/lap` and the true pace (`90.0s`) to within `0.06s`, with `R²` above `0.99`.
- Ran the full plotting code path against synthetic multi-stint data to confirm no runtime errors before testing against real data.

Once a machine with internet access was available, the tool was run against real 2025 season data (Silverstone) and confirmed working across all three modes end to end.

### Steps to Run

- Clone the repo and navigate into it.
- Create a virtual environment: `python -m venv .venv`, then activate it (`.venv\Scripts\activate` on Windows, `source .venv/bin/activate` on Mac/Linux).
- Install dependencies: `pip install -r requirements.txt`.
- Run one of the three modes:
  - Single-race stint degradation: `python task5.py stint --year 2025 --event Silverstone --session R --driver PIA`
  - Season-long drop-off trend: `python task5.py season --year 2025 --driver PIA`
  - Telemetry comparison: `python task5.py compare --year 2025 --event Silverstone --session Q --drivers PIA NOR`
- The first run downloads and caches session data locally (a `ff1_cache` folder is created automatically), so it can take a little while. Subsequent runs on the same session are much faster.
- Each command accepts an optional `--save path/to/file.png` flag to save the plot instead of just displaying it.

### Results
<img width="1000" height="600" alt="Figure_1" src="https://github.com/user-attachments/assets/341ebc08-c0a2-49c3-b1fd-9ccea16d3356" />
<img width="1536" height="752" alt="Figure_2" src="https://github.com/user-attachments/assets/fcdca6cc-865a-4c80-adcf-b9e6eb29ca5e" />
