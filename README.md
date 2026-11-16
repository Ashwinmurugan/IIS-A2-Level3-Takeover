# Level 3 Takeover Simulation

README prose word count: 1194 (excluding commands and this line).

## Project status

I am developing this project for Intelligent Interactive Systems Assignment 2 at the University of Birmingham, following my A1 review of speech and multimodal takeover warnings.

Iteration 1 is a feasibility prototype with three panels, webcam head-direction estimation, calibration, a keyboard-controlled practice road, sample speech and an event log. Phase 2 now adds gradual lane centring, manual lane changes and indicators, a tunnel warning sequence, head-turn prompts, escalation, simulated deceleration, demo audio priority and simulated vibration status. Vehicle movement is simplified. Other road scenarios remain planned.

## Technology and setup

Python 3.12, Pygame, OpenCV through opencv-contrib-python, MediaPipe and Windows SAPI through pywin32 are used. pyttsx3 remains installed from the feasibility iteration. Exact package versions are in requirements.txt. The current local environment uses the desktop application's bundled Python. Other reviewers should install Python 3.12 and create their own environment on Windows.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
New-Item -ItemType Directory models -Force
Invoke-WebRequest 'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task' -OutFile models/face_landmarker.task
.\.venv\Scripts\python.exe src/feasibility.py
```

The model is downloaded from Google's official MediaPipe distribution. The download is excluded from Git. Windows camera permission and an available webcam are needed. Camera frames are processed locally and never recorded by this application.

## Controls and checks

- C calibrates while I face the screen and hold still for two seconds.
- W/S change speed and A/D steer in manual mode.
- F selects simulated lane following. Space selects manual control.
- T plays a sample takeover message. Q/E toggle indicators. M toggles generated demo audio. R resets the tunnel scenario. Escape exits.
- Add --no-camera to run without the webcam, or --camera 1 to try another device.
- Run check_feasibility.py for driving calculations and a brief local camera check.
- Run src/feasibility.py --smoke for an automatic rendering check without camera or speech.

The estimated yaw threshold of 25 degrees and calibration settings are initial experimental choices. They need user testing. Head direction does not establish concentration or readiness. Missing or stale estimates produce an unavailable state.

## Development record

### 16 November 2026 — Design and feasibility

I chose a three-panel layout to demonstrate the interface alongside camera observations and rule decisions. I agreed to check camera, keyboard and speech behaviour before adding the complete tunnel interaction. The code was prepared with Codex assistance after I approved that scope.

Automatic checks passed for rendering, speed limits, stationary steering and constant-speed movement across different time steps. The camera check result is saved in evidence/feasibility-check.json. Calibration accuracy, head turns, audible speech and the feel of driving still require my interactive review.

The environment initially included two OpenCV distributions sharing the same module. These were replaced with the contrib distribution required by MediaPipe. The event log displays actual observed changes. Webcam images are excluded from saved evidence.

## AI assistance and sources

I used ChatGPT/Codex to discuss requirements, refine the interface, generate a concept image and implement this first feasibility version. I proposed live head monitoring, three panels and the observer log. I accepted explicit takeover confirmation and keyboard steering. I will record changes from my hands-on review in the next iteration.

The face model is pretrained by Google. The application uses MediaPipe's documented Face Landmarker API and its face transformation output. The model has not been trained on my data.

- MediaPipe documentation: https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker
- Pygame documentation: https://www.pygame.org/docs/
- Speech library: https://pypi.org/project/pyttsx3/

## Files and submission

src contains code, report is reserved for the report and diagrams, and evidence holds checks and screenshots. The report will link the public GitHub repository, README and submitted commit. Publishing details remain to be agreed. A ZIP is only needed for material that cannot reasonably go in the repository.


### 16 November 2026 — Integrated tunnel interaction

After trying the first build, I confirmed that the camera and keyboard commands worked. I asked for gradual centring, spoken control changes, lane indicators and integrated warnings before visual refinement. Codex implemented these changes following my approval.

The tunnel is placed 500 metres along the simulated road. Initial and urgent requests use experimental 15-second and 10-second time-to-boundary thresholds. A sustained two-second head turn after a request can trigger an attention prompt. Missing tracking does not suppress timed escalation. Simulated braking begins at six seconds remaining or when the calculated stopping distance plus a 15-metre margin requires it. Deceleration is 2.5 metres per second squared. These choices are prototype parameters, not validated driving recommendations.

The checks in src/driving.py passed for gradual centring, missing-camera fallback, stopping before the boundary, takeover continuity and attention prompting. Braking was checked at 20, 45 and 100 km/h with 30, 60 and 120 updates per second. The rendering check passed. A test initially allowed too little time after warning onset for the attention prompt; its duration was corrected. A road drawing overflow was also corrected.

Speech uses Windows SAPI asynchronously so new control messages can replace obsolete speech. M enables a locally generated tone as demonstration media. Warning activity and speech pause it. Saved run events contain timestamps and decisions, without webcam frames, and are excluded from Git until selected for evidence. Live calibration, spoken transitions, audio interruption and steering feel await my Phase 2 review.

Run src/driving.py to repeat the behavioural checks. The initial head-angle threshold and all driving logic remain simplified. Automatic lane changes and real traffic perception are future work.

### 16 November 2026 — Monitoring and feedback refinement

After testing Phase 2, I confirmed that the functionality worked and requested vertical head cues, possible eye monitoring, stronger alerts, larger fonts, realistic indicator arrows and visible key feedback. I approved keeping automation within the current lane.

Phase 3 adds a one-time Start drive screen, beginning in the right-hand lane of a two-lane same-direction simulated road. Enter or the start button begins movement. Calibration remains available before and after starting. Reset restarts the scenario without reopening setup. Automation identifies the current lane and smoothly centres within it, with an overshoot guard.

Head monitoring now uses calibrated yaw and pitch. Experimental thresholds are 25 degrees horizontally and 18 degrees vertically. MediaPipe eye-blink blendshape scores supply an apparent closure cue when both scores reach 0.65 for at least 1.5 seconds. A brief blink does not qualify. Missing face data resets closure timing. Sustained closure and non-forward orientation can trigger an attention prompt after two seconds during a takeover request. These are unvalidated prototype settings. Live direction labels and eye estimation require my camera review, including looking down and wearing glasses if relevant. The interface does not label the driver asleep.

The start screen explains calibration. Normal fonts increased by three points. Alerts use bold 32-point text, a warning triangle, contrasting background and persistent action/reason text. Amber arrows blink for direction signals. The keyboard strip highlights held keys and briefly highlights discrete presses. Dashboard mode feedback remains visible.

Synthetic checks passed for left/right/up/down classification, brief versus sustained closure, tracking-loss reset and lane centring from four positions. Previous braking and takeover checks still pass. Setup and alert states rendered successfully and were visually inspected. Generated smoke screenshots illustrate layouts using injected states, rather than recording a real driver trial. The latest camera check is in evidence/feasibility-check.json. Full live review of this iteration is pending.

Run src/monitoring.py for the new cue tests. Enter starts the drive; all previous driving controls remain available.
