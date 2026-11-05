NG GESTURE MOUSE CONTROL
========================

Control your Windows 11 mouse pointer with your built-in webcam and hand gestures.

RECOMMENDED:
- Windows 11, 64-bit
- Python 3.11 (64-bit)
- Built-in webcam
- Good, even lighting
- Keep your hand clearly visible to the camera

INSTALL:
1. Install Python 3.11 (64-bit) if it is not already installed.
   During installation, select "Add Python to PATH".
2. Double-click INSTALL_AND_RUN.bat.
3. Allow camera access if Windows asks.
4. A camera preview opens. Keep this window open while controlling the pointer.

GESTURES:
- Index finger raised alone: move the pointer.
- Pinch thumb and index finger briefly: left-click.
- Keep thumb and index pinched: drag; release to drop.
- Raise index and middle fingers, then move vertically: scroll.
- Hold the two-finger pose still: right-click.
- Show an open palm: pause all mouse actions.
- Make a fist for about one second: resume.
- Press B while the camera preview is active: turn title-bar button snap on/off.
- Press Q or ESC while the camera preview is active: quit.

SAFETY:
- Practise on an empty desktop first.
- Keep the camera preview visible.
- Open palm pauses control; make a fist to resume.
- Q or ESC exits the program.
- PyAutoGUI's top-left-corner failsafe is enabled. Hand gestures stop 1 pixel short of
  the exact corner, so the failsafe is triggered only by moving a physical mouse there.
- Do not use this as the only way to operate emergency or safety-critical software.
- Camera frames are processed locally; this project does not record or upload video.

TROUBLESHOOTING:
- If camera does not open, close Camera/Teams/Zoom and try again.
- Check Windows Settings > Privacy & security > Camera and allow desktop apps.
- If package installation fails, confirm Python 3.11 64-bit is installed.
- If cursor movement is reversed or jittery, adjust lighting and keep your hand inside the camera view.
- If gestures are detected poorly, face your palm toward the camera and move slowly.

SCREEN EDGES AND WINDOW BUTTONS (v2):
- The cyan box in the preview is the part of the camera view that covers the whole screen.
  Move your fingertip to the edge of that box to reach the matching screen edge or corner.
- Near the edge of the box the pointer goes the whole way to the screen edge.
- Movement is smoother when you move slowly and faster when you move quickly.
- Aiming at the top-right of the screen, the pointer snaps to Minimize, Maximize or Close
  (maximized windows, Windows 11 button size). Press B to turn this off.
- While you close thumb and index to pinch, the pointer is held still so the click lands
  where you aimed. Dragging now moves the pointer while the pinch is held.
- Tune these at the top of src/gesture_mouse.py: ACTIVE_X / ACTIVE_Y (hand travel),
  EDGE_SNAP (edge zone size), BUTTON_W / BUTTON_H / SNAP_RADIUS (button snap),
  PRE_PINCH_THRESHOLD (how early the pointer freezes), INVERT_X (left/right direction).

This project controls the operating-system pointer. It is separate from NG SmartPark.
