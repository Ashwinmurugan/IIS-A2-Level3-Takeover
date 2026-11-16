import os
"""Opt-in Other application audio session ducking. Never changes device/master volume."""


class AudioPriority:
    def __init__(self, emit, sessions=None):
        self.emit = emit
        if sessions is None:
            from pycaw.pycaw import AudioUtilities
            sessions = AudioUtilities.GetAllSessions
        self.sessions = sessions
        self.saved = []

    def lower(self):
        if self.saved:
            return
        try:
            for session in self.sessions():
                process = session.Process
                if process is None or process.pid == os.getpid():
                    continue
                volume = session.SimpleAudioVolume
                original = volume.GetMasterVolume()
                reduced = original * .15
                # Save before changing so partial failures can still be restored.
                self.saved.append((volume, original, reduced, process.name()))
                volume.SetMasterVolume(reduced, None)
                self.emit('Speech priority: lowered '+process.name())
            self.emit('Speech prioritised: Other application audio lowered' if self.saved else 'Other application audio priority unavailable: no Other application audio audio session on default output')
        except Exception as error:
            self.emit('Other application audio priority failed: '+str(error))
            self.restore()

    def restore(self):
        saved, self.saved = self.saved, []
        for volume, original, reduced, name in saved:
            try:
                current = volume.GetMasterVolume()
                if abs(current-reduced) < .001:
                    volume.SetMasterVolume(original,None)
                    self.emit('Previous audio volume restored: '+name)
                elif abs(current-original) >= .001:
                    self.emit('Other application audio volume changed externally; preserving new volume')
            except Exception as error:
                self.emit('Other application audio volume restoration failed: '+str(error))


def verify():
    class Volume:
        def __init__(self, value):
            self.value = value
        def GetMasterVolume(self):
            return self.value
        def SetMasterVolume(self,value,context):
            self.value = value
    class Process:
        def __init__(self,name):
            self.label = name
            self.pid = os.getpid() if name == 'python.exe' else os.getpid()+1
        def name(self):
            return self.label
    class Session:
        def __init__(self,name):
            self.Process = Process(name)
            self.SimpleAudioVolume = Volume(.8)
    spotify, other = Session('Other application audio.exe'), Session('python.exe')
    priority = AudioPriority(lambda message: None, lambda:[spotify,other])
    priority.lower()
    assert abs(spotify.SimpleAudioVolume.value-.12)<.001
    assert other.SimpleAudioVolume.value == .8
    priority.lower()
    priority.restore()
    assert spotify.SimpleAudioVolume.value == .8
    priority.lower()
    spotify.SimpleAudioVolume.value = .4
    priority.restore()
    assert spotify.SimpleAudioVolume.value == .4
    print('PASS: targeted Other application audio reduction, no repeated reduction, restoration and user-volume preservation')


if __name__ == '__main__':
    verify()
