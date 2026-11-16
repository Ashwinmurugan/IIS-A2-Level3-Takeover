# Level 3 Takeover Simulation

README prose word count: 1373 (excluding commands and this line).

## Project status

I am developing this project for Intelligent Interactive Systems Assignment 2 at the University of Birmingham, following my A1 review of speech and multimodal takeover warnings. The desktop prototype combines webcam head and eye cues, keyboard driving, contextual warnings and an observer log.

Implemented scenarios are a tunnel boundary, a stationary vehicle appearing ahead, and rain with simulated visibility loss. Lane following, manual takeover, warning escalation, fallback braking, hazard indicators and demo audio priority are implemented. Road sensing and vehicle dynamics are simulated. Vibration is represented visually. Camera tracking uses Google's pretrained model. Roadworks, real haptic hardware, broader external media control and real vehicle integration remain planned extensions.

## Setup and running

Use Windows and Python 3.12. Pygame draws the interface, OpenCV captures frames, MediaPipe estimates facial features and Windows SAPI through pywin32 speaks messages. Exact package versions are in requirements.txt. pyttsx3 remains installed from the first iteration. My current local environment uses the desktop application's bundled Python. Reviewers should create their own environment.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
New-Item -ItemType Directory models -Force
Invoke-WebRequest 'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task' -OutFile models/face_landmarker.task
.\.venv\Scripts\python.exe src/feasibility.py
```

Choose a scenario with the buttons or 1/2/3. Press C while facing forward with eyes open for two seconds, then Enter to start. Calibration estimates a forward reference. Camera frames stay local and are not recorded. Camera failure leaves timed warnings available.

- W/S accelerate and brake. A/D steer. Q/E toggle direction indicators.
- F requests automated lane following. Space requests manual control.
- During emergency braking, Space queues manual control until stopping. Ordinary and fallback takeovers remain immediate. Emergency braking can also activate in manual mode if a detected same-lane obstruction becomes imminent. This is a specific simulation design choice.
- M toggles generated demo audio. T tests scenario-specific speech.
- R restarts the selected scenario. Tab returns to scenario selection and resets the run.
- Page Up/Down or the wheel scrolls the log. End returns to live events. Escape exits.
- Use --no-camera or --camera 1 for camera alternatives. --scenario rain preselects rain. --config accepts another settings file.

## Configurable behaviour

Edit scenarios.json before launch. Each scenario has a starting speed, lane and event distance. Lane 0 is left and lane 1 is right on the same-direction two-lane road. Defaults use 45 km/h and lane 1.

The tunnel begins at 500 metres and is 200 metres long. Exit produces an availability announcement without engaging automation. The obstacle appears when our car reaches 100 metres, at road position 400 metres, and becomes detectable within 350 metres. Thus the initial gap is 300 metres. Adjacent-lane obstacles do not trigger a takeover request. Emergency braking uses gap, speed and estimated stopping distance. An unavoidable collision produces an explicit stopped collision outcome.

Rain starts at 350 metres and evolves over 35 seconds even while stopped. Intensity drives the rain drawing and simulated visibility. Automation reduces speed towards 30 km/h in rain and requests takeover below the configured visibility limit. Recovery must persist for three seconds. An existing takeover request remains active until takeover or fallback, even if visibility improves.

Rules include warning times, braking rates, margins and attention-prompt duration. The default tunnel warning thresholds are 15, 10 and 6 seconds. Other scenarios use elapsed response time after detection. Emergency braking uses 7 m/s² and fallback uses 2.5 m/s². These are experimental settings, not validated driving or regulatory requirements. Physical grip, traffic gaps and real road perception are outside this model.

Head thresholds are 25 degrees yaw and 18 degrees pitch. Both eye-blink scores must reach 0.65 for 1.5 seconds before apparent sustained closure is shown. Missing tracking resets the closure timer. Orientation and eye closure cannot establish concentration, readiness or sleep.

## Checks and evidence

```powershell
.\.venv\Scripts\python.exe test_scenarios.py
.\.venv\Scripts\python.exe src/monitoring.py
.\.venv\Scripts\python.exe check_feasibility.py
.\.venv\Scripts\python.exe src/feasibility.py --smoke --scenario rain
```

Scenario tests cover tunnel stops across three speeds and frame rates, exit announcements, lane centring, obstacle appearance and lane relevance, emergency braking, queued takeover, impossible stopping distance, rain fallback and recovery. Monitoring tests use synthetic inputs. The webcam check processes live frames without saving images. Smoke screenshots use injected states for layout inspection. Phase 5 live speech, timing and driving feel still require my interactive review. Saved run events contain timestamps and rule decisions, and are excluded from Git until selected for evidence.

## Development record — 16 November 2026

- I proposed three panels and approved camera, keyboard and speech feasibility. Checks passed and I confirmed the controls worked. Commit f2b21b0.
- I requested integrated tunnel warnings, gradual centring, spoken control changes and indicators. These were implemented and checked. Commit bc78ead.
- I requested up/down cues, possible eye monitoring, stronger alerts and visible keys. Tests covered closure timing and tracking loss. Commit 47c6025.
- My review found a stationary tunnel, weak symbols, small logs and hidden automation rejections. The next version added progression, hazards, bold scrolling logs, rejection speech and clean interruption handling. Commit 121ebd2.
- I requested selectable dynamic scenarios and contextual explanations. Phase 5 moved parameters into a validated configuration, added stationary-obstacle and rain state, and separated emergency mitigation from takeover timing. Tests exposed the need to distinguish sufficient stopping margin from unavoidable collision, and emergency lane holding was checked during review. Results are in evidence/phase5-checks.json.

## AI assistance and sources

I used ChatGPT/Codex for requirements discussion, a concept image, implementation and test assistance. I supplied the layout and feature requests, approved each phase and reported live behaviour. Codex generated code and performed automated and visual checks. My feedback led to changes in lane movement, warnings, logging and scenario design. The face model is pretrained by Google and has not been trained on my data.

- MediaPipe Face Landmarker documentation: https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker
- Pygame documentation: https://www.pygame.org/docs/
- NHTSA automation overview: https://www.nhtsa.gov/vehicle-safety/automated-vehicle-safety

## Files and submission

src contains code, report is reserved for the report and diagrams, and evidence contains checks and screenshots. The report will identify the submitted commit and link the public repository and README. Publishing remains to be agreed. An accompanying ZIP is only needed for material unsuitable for the repository.


### Phase 6 — Road obstruction, visible eye cues and audio priority

I requested rain at 350 metres, a breakdown marker and an obstruction message that includes what to do. The spoken message is now “Obstruction ahead. Slow down and take control.” The road obstruction includes a warning triangle and raised bonnet cue as scenario dressing. The system does not diagnose a mechanical fault or recommend an unchecked lane change.

The live eye panel now shows the current estimate, blendshape closure score and duration during driving. Detection thresholds remain unchanged pending camera review. Simulated seat and wheel symbols highlight during urgent warnings and braking. M controls generated demo audio; T plays the selected scenario's sample message.

P enables or disables optional Spotify speech priority, also available with --spotify-priority. It lowers Spotify desktop audio sessions on the default Windows output to 15 percent of their previous session volume while speech plays. It restores that volume afterward or on normal shutdown, while preserving externally changed volume. It never changes device master volume. Other applications and browser-based Spotify are not targeted. Hard termination or OS failure cannot guarantee restoration. The log records attempts, absence of a session and failures.

Pycaw provides session access (https://github.com/AndreMiras/pycaw). Fake-session tests passed for targeting, repeated calls, restoration and preserving a changed volume. A read-only Windows check found zero Spotify sessions during development, so live audio ducking remains unverified. All scenario and monitoring checks passed. Exact spoken wording and the 350-metre onset were checked. The eye panel's live accuracy and the visual breakdown marker await my review.


### Phase 7 — Broader audio priority and stopping explanations

I approved extending audio priority beyond Spotify and explaining why the car stops. P now enables lowering process-owned audio sessions on the default Windows output, excluding the prototype process. The --audio-priority option enables it at launch; the former option remains an alias. Session names and restoration outcomes are logged. System sounds and sessions without an identifiable process are skipped. Other outputs and exclusive audio paths are unverified. The earlier Spotify-only description records the previous iteration.

Fallback speech now explains that takeover was not confirmed. Emergency braking explains the obstruction. The dashboard retains the cause while stopped. Looking away remains an attention cue rather than the stopping cause. Fake-session tests cover protecting the prototype audio, reduction, repeated calls and restoration. Live cross-application audio testing remains pending.
