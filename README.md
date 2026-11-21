# Level 3 Takeover Simulation

README prose word count: 1226 (excluding command blocks, link destinations and this line).

## Project status and scope

I developed this desktop prototype for Intelligent Interactive Systems Assignment 2 at the University of Birmingham. It builds on my Assignment 1 question about whether a brief reason helps drivers understand a takeover request. The simulator pairs contextual speech with dashboard instructions, webcam head/eye estimates and keyboard control. A right-hand event log lets an observer inspect the decisions.

Three scenarios work: a tunnel boundary, heavy rain and a stationary vehicle. The prototype implements lane centring, manual takeover, warning escalation, automatic slowing, emergency braking, hazard indicators and optional audio prioritisation. Road sensing and vehicle movement are simulated. An on-screen cue represents seat vibration. Physical haptic hardware, real vehicle integration and participant evaluation remain planned. Webcam estimates provide attention cues rather than a validated assessment of driver readiness.

## Requirements and versions

Use a Windows computer with Python 3.12, a keyboard and an audio output. A webcam is needed for live monitoring; the simulation also runs without one. Internet access is needed for initial installation and the model download. Git is required only for the clone method below.

The current local launcher reports Python 3.12.15. The environment originally used Python 3.12.14. Main dependency pins in requirements.txt are Pygame 2.6.1, MediaPipe 1.2.3, opencv-contrib-python 5.0.0.93, NumPy 2.5.5, pywin32 312 and Pycaw 20260927. Install from that file to reproduce the declared environment. Setup on a separate reviewer's computer has not yet been verified.

Pygame renders the display, OpenCV captures camera frames, Google's pretrained MediaPipe Face Landmarker supplies facial estimates, and the project rules manage takeover decisions. Windows SAPI through pywin32 produces speech. Pycaw controls application audio sessions. pyttsx3 is retained in the dependency file from an earlier iteration; current speech uses SAPI directly.

## Step-by-step setup

### 1. Obtain the project

Open PowerShell in a folder where you want the project. Clone the public repository and enter it:

```powershell
git clone https://github.com/Ashwinmurugan/IIS-A2-Level3-Takeover.git
cd .\IIS-A2-Level3-Takeover
```

Alternatively, choose Code > Download ZIP on GitHub, extract the ZIP, and open PowerShell inside the extracted folder containing README.md, requirements.txt and src. All following commands run from this project folder.

### 2. Check Python and create the environment

Install Python 3.12 for Windows with the Python launcher if the first command is unavailable. Close and reopen PowerShell after installing it.

```powershell
py -3.12 --version
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Wait for installation to finish successfully. Calling the environment's executable directly avoids a separate activation step and PowerShell activation-policy changes.

### 3. Download the face model

The model is excluded from Git. Download it once into the models folder:

```powershell
New-Item -ItemType Directory -Path models -Force
Invoke-WebRequest 'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task' -OutFile .\models\face_landmarker.task
Test-Path .\models\face_landmarker.task
```

The final command should return True. The download URL uses Google's latest model location, so the model file is not version-pinned.

### 4. Launch

```powershell
.\.venv\Scripts\python.exe .\src\feasibility.py
```

The simulator opens full screen. Press F11 to toggle windowed mode. On later launches, repeat only the launch command from the project folder. run.ps1 is an optional shortcut using the same executable.

## First drive and controls

1. At the calibration dialog, face forward with eyes open and press C. Hold still for two seconds. Retry C if calibration fails. K skips the dialog for testing without a camera.
2. Select Tunnel, Road obstruction or Heavy rain using the buttons or 1/2/3. Press Enter or Start drive. The vehicle starts in manual mode in the right-hand lane.
3. Press F to engage automated driving. Watch the banner, road, speed and control mode. Press Space when takeover is requested. The mode and speech confirm a successful transfer.

| Key | Action |
| --- | --- |
| W / S | Accelerate / brake |
| A / D | Steer left / right |
| Q / E | Toggle left / right indicator |
| F / Space | Request automation / manual control |
| C | Recalibrate forward reference |
| R / Tab | Restart / return to scenario selection |
| M / T | Toggle demo audio / test scenario speech |
| P | Toggle other-application audio priority |
| Page Up / Down, mouse wheel | Scroll observer log |
| End / F11 / Esc | Return log to live / toggle full screen / exit |

During emergency braking, Space queues manual control until stopping. Ordinary and fallback takeovers transfer immediately. Emergency braking may also intervene in manual mode for an imminent same-lane obstruction. This behaviour is a simulation design choice.

Camera frames remain local and are not saved. Missing estimates display as unavailable while timed takeover warnings continue. Looking towards the road can trigger an action reminder; the driver still requests control with Space.

## Suggested inspection and alternatives

For the tunnel, press F and continue towards the boundary. In one run press Space at the warning; restart and leave it unanswered to see escalation, slowing, hazards and the stopped explanation. Compare rain and obstruction to inspect contextual messages. Default event distances are 500 m for the tunnel and 350 m for rain. An obstruction appears after 100 m at road position 400 m. Parameters, timings and margins are in scenarios.json.

These optional launches support different setups:

```powershell
.\.venv\Scripts\python.exe .\src\feasibility.py --windowed
.\.venv\Scripts\python.exe .\src\feasibility.py --no-camera
.\.venv\Scripts\python.exe .\src\feasibility.py --camera 1
.\.venv\Scripts\python.exe .\src\feasibility.py --scenario rain --audio-priority
```

With audio priority enabled, speech lowers other process-owned audio sessions to 15% of their previous volume, then restores them. The prototype process and sessions without an identifiable process are excluded. External volume changes are preserved. I confirmed live audio reduction worked on my Windows setup. Different outputs and exclusive audio paths remain unverified; force-closing may prevent restoration.

## Checks and troubleshooting

Run automated checks independently of a webcam or spoken output:

```powershell
.\.venv\Scripts\python.exe .\test_scenarios.py
.\.venv\Scripts\python.exe .\src\monitoring.py
.\.venv\Scripts\python.exe .\test_tracking_loss.py
.\.venv\Scripts\python.exe .\test_head_return.py
.\.venv\Scripts\python.exe .\src\audio_priority.py
.\.venv\Scripts\python.exe .\src\feasibility.py --smoke --scenario rain
```

Checks cover warning escalation, lane centring, braking, collision outcomes, rain recovery, tracking loss and head-return reminders. Simulated audio-session tests cover reduction, restoration and external changes. Smoke mode renders injected states and saves review screenshots under evidence. Historical screenshots may show earlier interfaces. Participant understanding and workload remain to be evaluated.

If the camera fails, close other camera applications, check Windows camera permissions, try --camera 1, or use --no-camera and K. For missing speech, check the Windows audio output, use T and read the event log. For a missing model, repeat step 3. For missing modules, repeat dependency installation using the same .venv executable. If the launcher reports a missing base Python, create a fresh environment with installed Python 3.12 and reinstall dependencies. Report an installation error with its exact message and Python version.

## Development record

- **16 November — interaction.** I proposed the three panels and tested camera, keyboard and speech feasibility ([f2b21b0](https://github.com/Ashwinmurugan/IIS-A2-Level3-Takeover/commit/f2b21b0)). My testing led to gradual centring, control announcements and clearer cues ([bc78ead](https://github.com/Ashwinmurugan/IIS-A2-Level3-Takeover/commit/bc78ead), [47c6025](https://github.com/Ashwinmurugan/IIS-A2-Level3-Takeover/commit/47c6025)).
- **16 November — dynamic scenarios.** I found a stationary tunnel and hidden automation rejections. Progression and visible rejection feedback addressed these issues ([121ebd2](https://github.com/Ashwinmurugan/IIS-A2-Level3-Takeover/commit/121ebd2)). Configurable rain and obstruction scenarios followed ([b1ea776](https://github.com/Ashwinmurugan/IIS-A2-Level3-Takeover/commit/b1ea776)); checks are in evidence/phase5-checks.json.
- **16 November — audio and recovery.** I requested broader audio priority, stopping explanations and return-forward reminders ([4f6ab28](https://github.com/Ashwinmurugan/IIS-A2-Level3-Takeover/commit/4f6ab28), [f90ccb1](https://github.com/Ashwinmurugan/IIS-A2-Level3-Takeover/commit/f90ccb1)). I manually checked scenarios, controls and audio.
- **17 November — visual review.** I removed the cockpit overlay after finding it obscured the road. The interface gained clearer instruments and scenery ([24398c0](https://github.com/Ashwinmurugan/IIS-A2-Level3-Takeover/commit/24398c0)). Synthetic rendering covered 22 interface states and three window sizes.
- **17 November — live correction.** I identified reversed up/down labels. Codex corrected the mapping and ran checks; I verified both directions with my webcam ([7443631](https://github.com/Ashwinmurugan/IIS-A2-Level3-Takeover/commit/7443631)).

## Contribution, assistance and files

I designed the layout, contributed code and developed warning, control-feedback and event-log requirements. I manually tested all three scenarios and used the results to direct revisions. ChatGPT/Codex assisted with Pygame implementation, MediaPipe integration, debugging, automated checks, report drafting and figures. I reviewed and adapted its output, including the webcam-label correction and visible vibration evidence in the storyboard. Google's pretrained model is reused without retraining.

src contains code; evidence contains selected checks and screenshots. Local timestamped runs are saved in evidence/runs and excluded from Git by default. The separate Canvas report includes architecture, illustrated interactions and the submitted revision.

Sources: [MediaPipe Face Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker), [Pygame](https://www.pygame.org/docs/), [Pycaw](https://github.com/AndreMiras/pycaw).
