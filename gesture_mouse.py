import time
import math
import cv2
import mediapipe as mp
import pyautogui

# NG Gesture Mouse Control
# Safety: press Q or ESC in the camera window to quit.
# Open palm pauses; make a fist to resume.

# ---------------------------------------------------------------- camera ---
CAMERA_INDEX = 0
FRAME_WIDTH = 960
FRAME_HEIGHT = 540
SMALL_PREVIEW = True            # shrink the preview window and park it bottom-left
PREVIEW_SIZE = (640, 360)

# ------------------------------------------------- cursor area / movement ---
# Part of the camera view that maps onto the WHOLE screen (0.0 - 1.0).
# A smaller box = less hand travel needed to reach the screen edges.
ACTIVE_X = (0.15, 0.85)
ACTIVE_Y = (0.10, 0.72)
# Inside this fraction of an edge of the active box the cursor goes all the
# way to the screen edge, so corners are easy to hit.
EDGE_SNAP = 0.04
# Keep 1 px away from the very edge so the cursor never lands on exactly (0, 0),
# which would trip PyAutoGUI's top-left failsafe by accident.
EDGE_PAD = 1
# Left/right direction. If moving your hand right moves the cursor left,
# flip this value.
INVERT_X = True

# Adaptive smoothing: slow hand = heavy smoothing (steady), fast hand = responsive.
SMOOTH_MIN = 0.10
SMOOTH_MAX = 0.65
SMOOTH_FULL_SPEED_PX = 350
# Extra steadiness near the top edge where the title-bar buttons are.
PRECISION_BAND_PX = 90
PRECISION_FACTOR = 0.5

# ------------------------------------- Minimize / Maximize / Close helper ---
# Magnetic snap to the window buttons in the top-right corner (maximized
# windows). Press B in the preview window to switch it on/off.
BUTTON_SNAP = True
BUTTON_W = 46                   # Windows 11 caption button size at 100% scaling
BUTTON_H = 32
SNAP_RADIUS = 34
SNAP_RELEASE_RADIUS = 44
SNAP_SWITCH_MARGIN = 8

# --------------------------------------------------------------- gestures ---
PINCH_THRESHOLD = 0.045
PINCH_RELEASE_THRESHOLD = 0.060   # hysteresis: stops flicker while holding a pinch
# While the fingers are closing in for a pinch the cursor is frozen, so the
# click lands where you were aiming instead of where your finger drifted to.
PRE_PINCH_THRESHOLD = 0.10
DRAG_HOLD_SECONDS = 0.35
RIGHT_CLICK_HOLD_SECONDS = 0.70
SCROLL_DEADZONE = 0.012
SCROLL_SENSITIVITY = 85


class CursorController:
    """Turns a fingertip position (0-1 in the camera view) into a screen pixel.

    Pure logic with no camera or mouse calls, so it is easy to test.
    """

    def __init__(self, screen_w, screen_h):
        self.sw = screen_w
        self.sh = screen_h
        self.x = screen_w / 2.0
        self.y = screen_h / 2.0
        self.button_snap = BUTTON_SNAP
        self.snap_target = None
        cy = BUTTON_H / 2.0
        self.targets = {
            "Close": (screen_w - BUTTON_W * 0.5, cy),
            "Maximize": (screen_w - BUTTON_W * 1.5, cy),
            "Minimize": (screen_w - BUTTON_W * 2.5, cy),
        }

    @staticmethod
    def _axis(n, lo, hi):
        t = (n - lo) / (hi - lo)
        t = min(1.0, max(0.0, t))
        if t <= EDGE_SNAP:
            return 0.0
        if t >= 1.0 - EDGE_SNAP:
            return 1.0
        # Re-scale the middle so there is no jump where the edge zones begin.
        return (t - EDGE_SNAP) / (1.0 - 2.0 * EDGE_SNAP)

    def _snap_to_buttons(self, x, y):
        dists = {n: math.hypot(x - p[0], y - p[1]) for n, p in self.targets.items()}
        nearest = min(dists, key=dists.get)
        cur = self.snap_target
        if cur is not None:
            if dists[cur] > SNAP_RELEASE_RADIUS:
                cur = None
            elif nearest != cur and dists[nearest] + SNAP_SWITCH_MARGIN < dists[cur]:
                cur = nearest
        if cur is None and dists[nearest] <= SNAP_RADIUS:
            cur = nearest
        self.snap_target = cur
        if cur is not None:
            return self.targets[cur]
        return x, y

    def update(self, nx, ny):
        """nx, ny: fingertip position in the camera view, 0-1. Returns (px, py)."""
        span_x = self.sw - 1 - 2 * EDGE_PAD
        span_y = self.sh - 1 - 2 * EDGE_PAD
        tx = self._axis(nx, *ACTIVE_X) * span_x + EDGE_PAD
        ty = self._axis(ny, *ACTIVE_Y) * span_y + EDGE_PAD

        dist = math.hypot(tx - self.x, ty - self.y)
        alpha = SMOOTH_MIN + (SMOOTH_MAX - SMOOTH_MIN) * min(1.0, dist / SMOOTH_FULL_SPEED_PX)
        if self.y < PRECISION_BAND_PX and dist < 80:
            alpha *= PRECISION_FACTOR
        self.x += (tx - self.x) * alpha
        self.y += (ty - self.y) * alpha
        if dist < 1.0:                       # finish the last pixel exactly
            self.x, self.y = tx, ty

        out_x, out_y = self.x, self.y
        if self.button_snap:
            out_x, out_y = self._snap_to_buttons(out_x, out_y)
        else:
            self.snap_target = None

        px = int(round(min(self.sw - 1 - EDGE_PAD, max(EDGE_PAD, out_x))))
        py = int(round(min(self.sh - 1 - EDGE_PAD, max(EDGE_PAD, out_y))))
        return px, py


def distance(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def fingers_up(lm):
    # Works best when your palm faces the camera and fingers point upward.
    return {
        "index": lm[8].y < lm[6].y,
        "middle": lm[12].y < lm[10].y,
        "ring": lm[16].y < lm[14].y,
        "pinky": lm[20].y < lm[18].y,
    }


def put_text(frame, text, y, color=(240, 245, 255), scale=0.62):
    cv2.putText(frame, text, (18, y), cv2.FONT_HERSHEY_SIMPLEX,
                scale, color, 2, cv2.LINE_AA)


if __name__ == "__main__":
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0
    SCREEN_W, SCREEN_H = pyautogui.size()
    controller = CursorController(SCREEN_W, SCREEN_H)

    mp_hands = mp.solutions.hands
    mp_draw = mp.solutions.drawing_utils
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        model_complexity=1,
        min_detection_confidence=0.65,
        min_tracking_confidence=0.60
    )

    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW if hasattr(cv2, "CAP_DSHOW") else 0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    if not cap.isOpened():
        raise SystemExit(
            "Could not open the webcam. Close apps using the camera and check Windows "
            "Settings > Privacy & security > Camera."
        )

    WINDOW = "NG Gesture Mouse Control - Q to quit"
    if SMALL_PREVIEW:
        cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(WINDOW, PREVIEW_SIZE[0], PREVIEW_SIZE[1])
        cv2.moveWindow(WINDOW, 20, max(0, SCREEN_H - PREVIEW_SIZE[1] - 90))

    paused = False
    pinch_active = False
    pinch_start = None
    pinch_dragging = False
    right_pose_start = None
    right_pose_latched = False
    last_scroll_y = None
    resume_fist_start = None
    last_click_time = 0.0
    last_pos = None
    status = "Show one hand to the camera"

    def release_drag():
        global pinch_dragging
        if pinch_dragging:
            try:
                pyautogui.mouseUp()
            except pyautogui.FailSafeException:
                pass
            pinch_dragging = False

    def move_cursor(lm):
        global last_pos
        nx = (1.0 - lm[8].x) if INVERT_X else lm[8].x
        pos = controller.update(nx, lm[8].y)
        if pos != last_pos:
            try:
                pyautogui.moveTo(pos[0], pos[1], duration=0)
                last_pos = pos
            except pyautogui.FailSafeException:
                pass

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                status = "Camera frame unavailable"
                break

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = hands.process(rgb)
            hand_found = bool(result.multi_hand_landmarks)

            if hand_found:
                hand = result.multi_hand_landmarks[0]
                lm = hand.landmark
                mp_draw.draw_landmarks(frame, hand, mp_hands.HAND_CONNECTIONS)
                up = fingers_up(lm)
                count = sum(up.values())
                open_palm = count == 4
                fist = count == 0
                pinch_dist = distance(lm[4], lm[8])
                # Hysteresis: easier to keep a pinch than to start one.
                pinch_active = pinch_dist < (PINCH_RELEASE_THRESHOLD if pinch_active
                                             else PINCH_THRESHOLD)
                pinch = pinch_active
                pre_pinch = pinch_dist < PRE_PINCH_THRESHOLD
                two_finger_pose = up["index"] and up["middle"] and not up["ring"] and not up["pinky"]

                # Open palm pauses all mouse actions. Make a fist to resume.
                if open_palm:
                    paused = True
                    release_drag()
                    pinch_active = False
                    pinch_start = None
                    right_pose_start = None
                    last_scroll_y = None
                    resume_fist_start = None
                    status = "PAUSED - make a fist to resume"
                elif paused:
                    if fist:
                        if resume_fist_start is None:
                            resume_fist_start = time.monotonic()
                        if time.monotonic() - resume_fist_start >= 0.8:
                            paused = False
                            resume_fist_start = None
                            status = "Resumed"
                    else:
                        resume_fist_start = None
                    if paused:
                        status = "PAUSED - hold a fist briefly to resume"
                else:
                    # Pinch: short pinch = left click; hold pinch = drag.
                    if pinch:
                        if pinch_start is None:
                            pinch_start = time.monotonic()
                            pinch_dragging = False
                        held = time.monotonic() - pinch_start
                        if held >= DRAG_HOLD_SECONDS and not pinch_dragging:
                            try:
                                pyautogui.mouseDown()
                                pinch_dragging = True
                            except pyautogui.FailSafeException:
                                status = "Safety stop: cursor reached top-left corner"
                        status = "Dragging" if pinch_dragging else "Pinch - hold to drag"
                    else:
                        if pinch_start is not None:
                            held = time.monotonic() - pinch_start
                            if not pinch_dragging and held < DRAG_HOLD_SECONDS:
                                if time.monotonic() - last_click_time > 0.25:
                                    try:
                                        pyautogui.click()
                                        last_click_time = time.monotonic()
                                        status = "Left click"
                                    except pyautogui.FailSafeException:
                                        status = "Safety stop: cursor reached top-left corner"
                            release_drag()
                            pinch_start = None

                    # Two raised fingers: move vertically to scroll.
                    # Hold still for a moment to perform one right-click.
                    if two_finger_pose and not pinch:
                        mid_y = (lm[8].y + lm[12].y) / 2
                        if right_pose_start is None:
                            right_pose_start = time.monotonic()
                            last_scroll_y = mid_y
                        delta = mid_y - last_scroll_y if last_scroll_y is not None else 0
                        if abs(delta) > SCROLL_DEADZONE:
                            amount = int(-delta * SCROLL_SENSITIVITY)
                            if amount == 0:
                                amount = -1 if delta > 0 else 1
                            try:
                                pyautogui.scroll(amount)
                            except pyautogui.FailSafeException:
                                pass
                            last_scroll_y = mid_y
                            right_pose_start = time.monotonic()
                            right_pose_latched = False
                            status = "Scrolling"
                        elif (time.monotonic() - right_pose_start >= RIGHT_CLICK_HOLD_SECONDS
                              and not right_pose_latched):
                            try:
                                pyautogui.rightClick()
                                status = "Right click"
                            except pyautogui.FailSafeException:
                                status = "Safety stop"
                            right_pose_latched = True
                    else:
                        right_pose_start = None
                        right_pose_latched = False
                        last_scroll_y = None

                    # Index finger moves the cursor. The cursor is frozen while the
                    # fingers close in for a pinch (accurate clicks), but follows
                    # your hand again once a drag has started.
                    pointing = up["index"] and not up["middle"] and not pre_pinch
                    if pointing or pinch_dragging:
                        move_cursor(lm)
                        if controller.snap_target:
                            status = "Snap: " + controller.snap_target
                        elif status not in ("Left click", "Dragging"):
                            status = "Move cursor"

            else:
                release_drag()
                pinch_active = False
                pinch_start = None
                right_pose_start = None
                right_pose_latched = False
                last_scroll_y = None
                if not paused:
                    status = "No hand detected"

            # On-screen instructions
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (frame.shape[1], 112), (10, 20, 35), -1)
            frame = cv2.addWeighted(overlay, 0.78, frame, 0.22, 0)
            put_text(frame, "NG GESTURE MOUSE CONTROL", 28, (100, 220, 255), 0.7)
            put_text(frame, "Index: move | Thumb+index pinch: click / hold: drag", 55)
            put_text(frame, "Two fingers: scroll by moving | Hold still: right-click", 80)
            put_text(frame, "Open palm: PAUSE | Fist: RESUME | B: button snap | Q / ESC: QUIT", 105)
            color = (90, 230, 160) if not paused else (70, 150, 255)
            put_text(frame, "STATUS: " + status, frame.shape[0] - 22, color, 0.65)

            # Show the area of the camera view that covers the whole screen.
            fh, fw = frame.shape[:2]
            if INVERT_X:
                bx0, bx1 = 1.0 - ACTIVE_X[1], 1.0 - ACTIVE_X[0]
            else:
                bx0, bx1 = ACTIVE_X
            cv2.rectangle(frame, (int(bx0 * fw), int(ACTIVE_Y[0] * fh)),
                          (int(bx1 * fw), int(ACTIVE_Y[1] * fh)), (100, 220, 255), 1)

            cv2.imshow(WINDOW, frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            if key in (ord("b"), ord("B")):
                controller.button_snap = not controller.button_snap
                status = "Button snap " + ("ON" if controller.button_snap else "OFF")

    finally:
        release_drag()
        cap.release()
        hands.close()
        cv2.destroyAllWindows()
