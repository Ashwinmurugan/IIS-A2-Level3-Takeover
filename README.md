# Level 3 Takeover Simulation

README prose word count: 563 (excluding commands and this line).

## Project status

I am developing this project for Intelligent Interactive Systems Assignment 2 at the University of Birmingham, following my A1 review of speech and multimodal takeover warnings.

Iteration 1 is a feasibility prototype with three panels, webcam head-direction estimation, calibration, a keyboard-controlled practice road, sample speech and an event log. The full tunnel warning sequence, escalation, simulated deceleration, media priority and vibration indicators are planned. Vehicle movement is simplified. The road currently supports practice only.

## Technology and setup

Python 3.12, Pygame, OpenCV through opencv-contrib-python, MediaPipe and pyttsx3 are used. Exact package versions are in requirements.txt. The current local environment uses the desktop application's bundled Python. Other reviewers should install Python 3.12 and create their own environment on Windows.

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
- T plays a sample takeover message. R resets the road. Escape exits.
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

