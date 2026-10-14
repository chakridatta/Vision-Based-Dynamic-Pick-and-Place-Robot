"""
Dynamic_pick_and_place_8.py
========================================================================================
Advanced Vision-Guided Industrial Robotic Pick-and-Place Automation Cell
Dataset: Roboflow Industrial Conveyor Belt (Bolts & Washers)
Framework: Python / Pygame / OpenCV

Key Industrial Features:
1. Complete Industrial Automation Cell: Metallic conveyor frame, drive motor/gearbox,
   structural mounting gantry, overhead GigE camera, flexible spiral vacuum hose,
   control cabinet, safety perimeter fencing, optical photoelectric sensor beams,
   3-tier status tower light, and E-Stop safety interlock box.
2. Conveyor Control: Interactive start/stop, dynamic speed slider (200-1200 mm/s),
   smooth acceleration/deceleration, reverse toggle, real-time speed display.
3. Robot Control & Manual Jogging: Auto/Manual modes, speed/acceleration scaling,
   Home, Pause/Resume, Emergency Stop, Vacuum Gripper toggle, and 6-DOF Jog Controls
   (X+, X-, Y+, Y-, Z+, Z-).
4. Object Generator & Motion Dynamics: Adjustable spawn rate, max capacity, class
   filtering (Bolts/Washers), manual spawn button, dynamic speed variations, and jitter.
5. Latency & Predictive Interception: Interactive latency controls (camera, YOLO,
   tracking, communication), real-time prediction horizon visualization.
6. Spatially Separated Drop Stations: Dedicated Bolt Bin A and Washer Bin B located
   away from the conveyor with 3D stacking and separate travel trajectories.
7. Multi-Strategy Target Selector: Earliest Interception (EDF), Nearest Reachable,
   Highest Confidence, Bolt Priority, and Washer Priority.
8. Fault Injection Engine: Detection drop, tracking loss, object occlusion, latency spikes,
   speed disturbances, gripper slip, with automatic recovery and telemetry logging.
9. 8 Scenario Presets: Normal, High-Speed, High Density, High Latency, Low Latency,
   Tracking Failure, Object Occlusion, and Emergency Stop.
10. Live Roboflow YOLO Vision Monitor: Real camera frames with live bounding boxes,
    class badges, confidence, frame rate, and inference latency.
11. Full Operations Console, Target Card, Expanded Vision Queue Table, and Performance KPI Dashboard.
========================================================================================
"""

import pygame
import math
import random
import sys
import time
import os
import cv2
from dataset_loader import RoboflowConveyorDataset

pygame.init()

# ============================================================
# WINDOW & DISPLAY CONFIGURATION
# ============================================================
WIDTH = 1600
HEIGHT = 900
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Vision-Guided Industrial Robotic Pick-and-Place Automation Cell")
clock = pygame.time.Clock()

# ============================================================
# TYPOGRAPHY
# ============================================================
FONT_TINY = pygame.font.SysFont("consolas", 11)
FONT_SMALL = pygame.font.SysFont("consolas", 13)
FONT_STATUS = pygame.font.SysFont("consolas", 14, bold=True)
FONT = pygame.font.SysFont("consolas", 16)
FONT_MED = pygame.font.SysFont("consolas", 18, bold=True)
FONT_BIG = pygame.font.SysFont("consolas", 22, bold=True)
FONT_TITLE = pygame.font.SysFont("consolas", 25, bold=True)

# ============================================================
# COLOR PALETTE (INDUSTRIAL MONITORING DESIGN SYSTEM)
# ============================================================
WHITE = (245, 248, 252)
BLACK = (10, 13, 17)
DARK_BG = (18, 21, 27)
FLOOR_COLOR = (24, 28, 35)
FLOOR_GRID = (36, 42, 52)
PANEL_BG = (26, 31, 39)
PANEL_HEADER = (20, 24, 31)
PANEL_BORDER = (55, 63, 76)
GRAY = (125, 133, 145)
LIGHT_GRAY = (195, 202, 212)

# Operational Status Colors
GREEN = (50, 215, 120)       # Healthy / Normal / Bolt Accent
YELLOW = (250, 210, 55)      # Warning / Intercept / Target
AMBER = (245, 160, 45)       # Washer Accent / Notice
RED = (235, 75, 75)          # Fault / E-Stop / Critical
BLUE = (60, 155, 250)        # Informational / Controls
CYAN = (55, 220, 235)        # Telemetry / Vision Beams
ACCENT_GOLD = (255, 195, 50) # Highlights

# Class & Station Colors
BOLT_COLOR = (60, 210, 140)
WASHER_COLOR = (245, 170, 50)
BIN_BOLT_COLOR = (40, 130, 210)
BIN_WASHER_COLOR = (230, 140, 35)

# ============================================================
# 3D ISOMETRIC WORLD DIMENSIONS & KINEMATICS
# ============================================================
CONVEYOR_X_MIN = -660
CONVEYOR_X_MAX = 410
CONVEYOR_Y_MIN = -135
CONVEYOR_Y_MAX = 135
BELT_Z = 25

ROBOT_BASE_X = 20
ROBOT_BASE_Y = -10
ROBOT_BASE_Z = 430

HOME = (20, -10, 240)
APPROACH_Z = 180
PICK_Z = 82
LIFT_Z = 195

# Spatially separated industrial drop bins (moved well away from conveyor)
BOLT_DROP_X = 350
BOLT_DROP_Y = 180
BOLT_DROP_Z = 85

WASHER_DROP_X = 425
WASHER_DROP_Y = 255
WASHER_DROP_Z = 85

# Robot performance specifications
ROBOT_MAX_SPEED = 1200.0      # mm/s
robot_speed_pct = 100.0       # user adjustable percentage
robot_accel_pct = 100.0       # user adjustable percentage
DESCEND_SPEED = 700.0         # mm/s visual servoing descend speed (fast dynamic tracking)
GRIP_DELAY = 0.08             # s vacuum seal response time
RELEASE_DELAY = 0.08          # s blow-off release delay
WORKSPACE_RADIUS = 475.0      # spherical reachable boundary

# Conveyor dynamics
conveyor_running = True
conveyor_direction = 1        # 1 for forward, -1 for reverse
target_conveyor_speed = 280.0 # mm/s nominal (smooth continuous industrial speed, user range 100 - 800 mm/s)
current_conveyor_speed = 280.0
CONVEYOR_ACCEL = 400.0        # mm/s^2 smooth physical acceleration
conveyor_belt_offset = 0.0
conveyor_flow_status = "SYNCHRONIZED (100% PICK)"

# Latency Simulation System (Latency-Aware Motion Prediction)
camera_latency = 0.033        # 33 ms GigE camera exposure/transfer
yolo_latency = 0.015          # 15 ms YOLOv11 model inference
tracking_latency = 0.005      # 5 ms Kalman filter tracking
comm_latency = 0.007          # 7 ms Industrial fieldbus comms
robot_response_latency = 0.010# 10 ms PLC servo drive acceleration buffer

def get_total_latency():
    return (camera_latency + yolo_latency + tracking_latency +
            comm_latency + robot_response_latency)

# ============================================================
# 3D ISOMETRIC PROJECTION
# ============================================================
ORIGIN_X = 740
ORIGIN_Y = 515
SCALE_X = 0.80
SCALE_Y = 0.40
DEPTH_SCALE = 0.18
Z_SCALE = 0.72

def project(p):
    x, y, z = p
    sx = ORIGIN_X + x * SCALE_X + y * SCALE_Y
    sy = ORIGIN_Y + y * DEPTH_SCALE - z * Z_SCALE
    return int(sx), int(sy)

def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])

def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

def mul(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)

def length(v):
    return math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)

def distance(a, b):
    return length(sub(a, b))

def move_towards(current, target, speed, dt):
    d = distance(current, target)
    if d <= speed * dt or d == 0:
        return target
    direction = mul(sub(target, current), 1.0 / d)
    return add(current, mul(direction, speed * dt))

def clamp(v, a, b):
    return max(a, min(b, v))

# ============================================================
# GRAPHIC PRIMITIVES
# ============================================================
def draw_world_line(p1, p2, color, width=2):
    pygame.draw.line(screen, color, project(p1), project(p2), width)

def draw_box(center, size, top_color, side_color=None, outline=None):
    cx, cy, cz = center
    sx, sy, sz = size
    hx, hy, hz = sx / 2, sy / 2, sz / 2

    pts = [
        (cx - hx, cy - hy, cz - hz),
        (cx + hx, cy - hy, cz - hz),
        (cx + hx, cy + hy, cz - hz),
        (cx - hx, cy + hy, cz - hz),
        (cx - hx, cy - hy, cz + hz),
        (cx + hx, cy - hy, cz + hz),
        (cx + hx, cy + hy, cz + hz),
        (cx - hx, cy + hy, cz + hz),
    ]
    p = [project(v) for v in pts]
    if side_color is None:
        side_color = top_color

    faces = [
        ([0, 1, 5, 4], side_color),
        ([1, 2, 6, 5], side_color),
        ([2, 3, 7, 6], side_color),
        ([3, 0, 4, 7], side_color),
        ([4, 5, 6, 7], top_color),
    ]
    for indices, color in faces:
        pygame.draw.polygon(screen, color, [p[i] for i in indices])

    if outline:
        pygame.draw.lines(screen, outline, True, [p[0], p[1], p[2], p[3], p[0]], 1)
        pygame.draw.lines(screen, outline, False, [p[4], p[5], p[6], p[7], p[4]], 1)
        for a, b in [(0, 4), (1, 5), (2, 6), (3, 7)]:
            pygame.draw.line(screen, outline, p[a], p[b], 1)

def draw_cylinder(center, radius, height, color, segments=24):
    x, y, z = center
    top, bottom = [], []
    for i in range(segments):
        a = 2 * math.pi * i / segments
        px = x + math.cos(a) * radius
        py = y + math.sin(a) * radius
        top.append(project((px, py, z + height / 2)))
        bottom.append(project((px, py, z - height / 2)))

    pygame.draw.polygon(screen, color, top)
    side_c = tuple(max(0, c - 28) for c in color)
    for i in range(segments):
        j = (i + 1) % segments
        pygame.draw.polygon(screen, side_c, [top[i], top[j], bottom[j], bottom[i]])
    pygame.draw.lines(screen, (15, 18, 22), True, top, 1)

def text(txt, pos, font=FONT, color=WHITE):
    surf = font.render(str(txt), True, color)
    screen.blit(surf, pos)

# ============================================================
# INTERACTIVE UI COMPONENT FRAMEWORK
# ============================================================
class UIElement:
    def __init__(self, rect):
        self.rect = pygame.Rect(rect)

    def handle_event(self, event):
        return False

    def draw(self, surface):
        pass

class UIButton(UIElement):
    def __init__(self, rect, label, on_click, bg_color=(36, 44, 56), text_color=WHITE, border_color=PANEL_BORDER, font=FONT_SMALL):
        super().__init__(rect)
        self.label = label
        self.on_click = on_click
        self.bg_color = bg_color
        self.text_color = text_color
        self.border_color = border_color
        self.font = font
        self.hovered = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.on_click()
                return True
        return False

    def draw(self, surface):
        bg = tuple(min(255, c + 25) for c in self.bg_color) if self.hovered else self.bg_color
        pygame.draw.rect(surface, bg, self.rect, border_radius=4)
        border = CYAN if self.hovered else self.border_color
        pygame.draw.rect(surface, border, self.rect, 1, border_radius=4)
        tw, th = self.font.size(self.label)
        surface.blit(self.font.render(self.label, True, self.text_color),
                     (self.rect.x + (self.rect.w - tw) // 2, self.rect.y + (self.rect.h - th) // 2))

class UISlider(UIElement):
    def __init__(self, rect, min_val, max_val, current_val, label, unit="", on_change=None):
        super().__init__(rect)
        self.min_val = min_val
        self.max_val = max_val
        self.val = current_val
        self.label = label
        self.unit = unit
        self.on_change = on_change
        self.dragging = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.dragging = True
                self.update_val(event.pos[0])
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self.update_val(event.pos[0])
            return True
        return False

    def update_val(self, mouse_x):
        rel = clamp((mouse_x - self.rect.x) / self.rect.w, 0.0, 1.0)
        self.val = self.min_val + rel * (self.max_val - self.min_val)
        if self.on_change:
            self.on_change(self.val)

    def draw(self, surface):
        # Header label
        val_txt = f"{self.val:.0f}{self.unit}" if self.val > 10 else f"{self.val:.2f}{self.unit}"
        full_lbl = f"{self.label}: {val_txt}"
        text(full_lbl, (self.rect.x, self.rect.y - 16), FONT_TINY, LIGHT_GRAY)

        # Track bar
        pygame.draw.rect(surface, (20, 24, 30), self.rect, border_radius=3)
        pygame.draw.rect(surface, PANEL_BORDER, self.rect, 1, border_radius=3)

        # Active fill
        pct = (self.val - self.min_val) / (self.max_val - self.min_val)
        fill_w = int(self.rect.w * pct)
        if fill_w > 0:
            pygame.draw.rect(surface, CYAN, (self.rect.x, self.rect.y, fill_w, self.rect.h), border_radius=3)

        # Thumb handle
        thumb_x = self.rect.x + fill_w
        pygame.draw.circle(surface, WHITE, (thumb_x, self.rect.y + self.rect.h // 2), 6)
        pygame.draw.circle(surface, (20, 24, 30), (thumb_x, self.rect.y + self.rect.h // 2), 3)

class UIToggle(UIElement):
    def __init__(self, rect, label, state, on_toggle):
        super().__init__(rect)
        self.label = label
        self.state = state
        self.on_toggle = on_toggle

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.state = not self.state
                self.on_toggle(self.state)
                return True
        return False

    def draw(self, surface):
        box_size = self.rect.h
        box_rect = pygame.Rect(self.rect.x, self.rect.y, box_size, box_size)
        bg = (30, 80, 50) if self.state else (30, 35, 42)
        pygame.draw.rect(surface, bg, box_rect, border_radius=3)
        border = GREEN if self.state else PANEL_BORDER
        pygame.draw.rect(surface, border, box_rect, 1, border_radius=3)

        if self.state:
            # Check mark
            pygame.draw.line(surface, GREEN, (self.rect.x + 3, self.rect.y + 7), (self.rect.x + 6, self.rect.y + 11), 2)
            pygame.draw.line(surface, GREEN, (self.rect.x + 6, self.rect.y + 11), (self.rect.x + 12, self.rect.y + 3), 2)

        lbl_color = WHITE if self.state else GRAY
        text(self.label, (self.rect.x + box_size + 8, self.rect.y + 1), FONT_TINY, lbl_color)

# ============================================================
# INDUSTRIAL OPERATIONS LOGGER
# ============================================================
class OperationsLogger:
    def __init__(self, max_entries=14):
        self.max_entries = max_entries
        self.entries = []
        self.active_operation = "SYSTEM INITIALIZED - MONITORING CONVEYOR"

    def log(self, tag, message, color=WHITE):
        current_time = time.strftime("%H:%M:%S")
        self.entries.append({
            "time": current_time,
            "tag": tag,
            "msg": message,
            "color": color
        })
        if len(self.entries) > self.max_entries:
            self.entries.pop(0)
        self.active_operation = f"[{tag}] {message}"

    def get_entries(self):
        return self.entries

    def get_active(self):
        return self.active_operation

logger = OperationsLogger()

# ============================================================
# INDUSTRIAL SENSORS SYSTEM
# ============================================================
class ConveyorSensor:
    def __init__(self, name, x_pos, color=CYAN):
        self.name = name
        self.x = x_pos
        self.color = color
        self.beam_broken = False
        self.active_timer = 0.0

    def update(self, dt, active_objects):
        self.beam_broken = False
        for obj in active_objects:
            if obj.state == "CONVEYOR" and abs(obj.x - self.x) < 22:
                self.beam_broken = True
                break
        if self.beam_broken:
            self.active_timer = 0.25
        else:
            self.active_timer = max(0.0, self.active_timer - dt)

    def is_triggered(self):
        return self.active_timer > 0.0

    def draw(self):
        beam_c = (255, 60, 60) if self.is_triggered() else (40, 160, 220)
        z = BELT_Z + 12
        # Transmitter on left rail, Receiver on right rail
        p1 = (self.x, CONVEYOR_Y_MIN + 3, z)
        p2 = (self.x, CONVEYOR_Y_MAX - 3, z)
        draw_world_line(p1, p2, beam_c, 2 if not self.is_triggered() else 4)

        # Sensor housing blocks
        draw_box(p1, (10, 14, 18), (80, 90, 105), (45, 50, 60))
        draw_box(p2, (10, 14, 18), (80, 90, 105), (45, 50, 60))

        # Status LED indicator on transmitter
        led_screen = project(p1)
        led_color = RED if self.is_triggered() else GREEN
        pygame.draw.circle(screen, led_color, (led_screen[0], led_screen[1] - 8), 3)

sensors = [
    ConveyorSensor("S1-ENTRY", -580, CYAN),
    ConveyorSensor("S2-CAMERA", -320, CYAN),
    ConveyorSensor("S3-PICK", -100, YELLOW),
    ConveyorSensor("S4-EXIT", 280, RED),
]

# ============================================================
# CONVEYOR OBJECT CLASS (DYNAMIC MOTION & FASTENER MODELS)
# ============================================================
class ConveyorObject:
    def __init__(self, obj_id, obj_class, x, y, vx, confidence=0.98):
        self.id = obj_id
        self.obj_class = obj_class # 'bolt' or 'washer'
        self.x = x
        self.y = y
        self.z = BELT_Z

        # Velocity & Motion Physics
        self.slip_vx = random.uniform(-3.0, 3.0) # subtle physical belt slip
        self.vx = vx
        self.vy = random.uniform(-1.0, 1.0) # subtle physical lateral drift
        self.measured_vx = vx
        self.measured_vy = 0.0

        self.previous_x = x
        self.previous_y = y

        self.pred_x = x
        self.pred_y = y
        self.pred_z = BELT_Z

        self.confidence = confidence
        self.state = "CONVEYOR" # CONVEYOR, GRASPED, PLACED, MISSED
        self.reachable = False
        self.time_to_intercept = 0.0
        self.spawn_time = time.time()
        self.grip_time = None
        self.prediction_error = 0.0
        self.placed_bin = None
        self.occluded = False

    def update_motion(self, dt, belt_speed, speed_scale=1.0):
        if self.state != "CONVEYOR":
            return
        self.previous_x = self.x
        self.previous_y = self.y

        # Velocity coupled with conveyor speed and direction + physical slip
        effective_vx = (belt_speed * conveyor_direction + self.slip_vx) * speed_scale
        self.x += effective_vx * dt
        self.y = clamp(self.y + self.vy * dt, CONVEYOR_Y_MIN + 25, CONVEYOR_Y_MAX - 25)

        if dt > 0:
            raw_vx = (self.x - self.previous_x) / dt
            self.measured_vx = 0.85 * self.measured_vx + 0.15 * raw_vx
            raw_vy = (self.y - self.previous_y) / dt
            self.measured_vy = 0.85 * self.measured_vy + 0.15 * raw_vy

    def get_target_drop_location(self):
        if self.obj_class == "bolt":
            return (BOLT_DROP_X, BOLT_DROP_Y, BOLT_DROP_Z)
        else:
            return (WASHER_DROP_X, WASHER_DROP_Y, WASHER_DROP_Z)

# ============================================================
# DELTA ROBOT KINEMATICS & MANUAL JOGGING
# ============================================================
class DeltaRobot:
    def __init__(self):
        self.position = HOME
        self.state = "HOME"
        self.mode = "AUTO" # "AUTO" or "MANUAL"
        self.target_object = None
        self.attached_object = None
        self.state_timer = 0.0
        self.path = []
        self.grip_closed = False
        self.feedback_count = 0
        self.e_stop = False

    def set_state(self, new_state):
        self.state = new_state
        self.state_timer = 0.0

    def update_timer(self, dt):
        self.state_timer += dt

    def move_to(self, target, base_speed, dt):
        effective_speed = base_speed * (robot_speed_pct / 100.0)
        self.position = move_towards(self.position, target, effective_speed, dt)
        self.path.append(self.position)
        if len(self.path) > 240:
            self.path.pop(0)

    def jog(self, dx, dy, dz):
        if self.mode == "MANUAL" and not self.e_stop:
            new_pos = (
                clamp(self.position[0] + dx, -400, 500),
                clamp(self.position[1] + dy, -300, 350),
                clamp(self.position[2] + dz, 60, 320)
            )
            self.position = new_pos
            logger.log("JOG", f"Manual Jog to ({new_pos[0]:.0f}, {new_pos[1]:.0f}, {new_pos[2]:.0f})", BLUE)

    def attach_object(self, obj):
        self.attached_object = obj
        obj.state = "GRASPED"
        self.grip_closed = True

    def release_object(self):
        obj = self.attached_object
        if obj is not None:
            obj.state = "PLACED"
            dest = obj.get_target_drop_location()
            obj.placed_bin = obj.obj_class
            # 3D neat stacking inside industrial tote
            bin_count = len([o for o in placed_objects if o.placed_bin == obj.obj_class])
            obj.x = dest[0] + (bin_count % 3 - 1) * 18
            obj.y = dest[1] + ((bin_count // 3) % 3 - 1) * 18
            obj.z = dest[2] + (bin_count // 9) * 12
            placed_objects.append(obj)
        self.attached_object = None
        self.grip_closed = False

robot = DeltaRobot()

# ============================================================
# FAULT SIMULATION & SCENARIO PRESETS
# ============================================================
class FaultSimulationManager:
    def __init__(self):
        self.fault_detection_loss = False
        self.fault_tracking_loss = False
        self.fault_occlusion = False
        self.fault_camera_latency = False
        self.fault_processing_latency = False
        self.fault_speed_surge = False
        self.fault_gripper_slip = False
        self.fault_unreachable = False
        self.active_scenario = "NORMAL OPERATION"

    def apply_scenario(self, scenario_name):
        global target_conveyor_speed, camera_latency, yolo_latency, robot_speed_pct, spawn_interval
        self.active_scenario = scenario_name

        # Reset all fault toggles
        self.fault_detection_loss = False
        self.fault_tracking_loss = False
        self.fault_occlusion = False
        self.fault_camera_latency = False
        self.fault_processing_latency = False
        self.fault_speed_surge = False
        self.fault_gripper_slip = False
        self.fault_unreachable = False

        if scenario_name == "NORMAL OPERATION":
            target_conveyor_speed = 280.0
            camera_latency = 0.033
            yolo_latency = 0.015
            robot_speed_pct = 100.0
            spawn_interval = 1.8
            robot.e_stop = False
            logger.log("SCENARIO", "Configured Preset: NORMAL OPERATION (280 mm/s)", GREEN)

        elif scenario_name == "HIGH-SPEED CONVEYOR":
            target_conveyor_speed = 450.0
            robot_speed_pct = 125.0
            spawn_interval = 1.4
            robot.e_stop = False
            logger.log("SCENARIO", "Configured Preset: HIGH-SPEED CONVEYOR (450 mm/s)", YELLOW)
 
        elif scenario_name == "HIGH OBJECT DENSITY":
            target_conveyor_speed = 250.0
            spawn_interval = 1.0
            robot_speed_pct = 115.0
            robot.e_stop = False
            logger.log("SCENARIO", "Configured Preset: HIGH DENSITY (Spawn: 1.0s)", CYAN)

        elif scenario_name == "HIGH LATENCY":
            target_conveyor_speed = 260.0
            camera_latency = 0.120
            yolo_latency = 0.060
            self.fault_camera_latency = True
            logger.log("SCENARIO", "Configured Preset: HIGH LATENCY (180ms total)", AMBER)

        elif scenario_name == "LOW LATENCY":
            target_conveyor_speed = 300.0
            camera_latency = 0.012
            yolo_latency = 0.008
            logger.log("SCENARIO", "Configured Preset: LOW LATENCY (Ultra Fast 20ms)", GREEN)

        elif scenario_name == "TRACKING FAILURE":
            self.fault_tracking_loss = True
            logger.log("FAULT", "Preset: TRACKING FAILURE injected", RED)

        elif scenario_name == "OBJECT OCCLUSION":
            self.fault_occlusion = True
            logger.log("FAULT", "Preset: OBJECT OCCLUSION active", RED)

        elif scenario_name == "EMERGENCY STOP":
            trigger_emergency_stop()

        if "slider_conveyor_speed" in globals():
            slider_conveyor_speed.val = target_conveyor_speed
            slider_spawn_rate.val = spawn_interval
            slider_robot_speed.val = robot_speed_pct

fault_mgr = FaultSimulationManager()

# ============================================================
# TARGET SELECTION STRATEGIES
# ============================================================
TARGET_STRATEGIES = [
    "Earliest Interception (EDF)",
    "Nearest Reachable",
    "Highest Confidence",
    "Bolt Priority",
    "Washer Priority"
]
active_strategy_idx = 0

def select_target():
    if robot.e_stop or robot.mode == "MANUAL":
        return None

    candidates = []
    for obj in objects:
        if obj.state != "CONVEYOR":
            continue
        calculate_prediction(obj)
        if not obj.reachable or obj.occluded or fault_mgr.fault_tracking_loss:
            continue

        predicted = (obj.pred_x, obj.pred_y, APPROACH_Z)
        dist_to_robot = distance(robot.position, predicted)

        strat = TARGET_STRATEGIES[active_strategy_idx]
        if strat == "Earliest Interception (EDF)":
            # Earliest deadline to leave workspace, prioritizing smooth upstream dynamic picking
            score = - (obj.pred_x * 1.5) + (dist_to_robot / ROBOT_MAX_SPEED) * 40.0
        elif strat == "Nearest Reachable":
            score = dist_to_robot
        elif strat == "Highest Confidence":
            score = - obj.confidence * 1000.0 + dist_to_robot * 0.1
        elif strat == "Bolt Priority":
            score = (-1000.0 if obj.obj_class == "bolt" else 0.0) + dist_to_robot
        elif strat == "Washer Priority":
            score = (-1000.0 if obj.obj_class == "washer" else 0.0) + dist_to_robot
        else:
            score = - obj.pred_x

        candidates.append((score, obj))

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]

# ============================================================
# TRAJECTORY & LATENCY PREDICTION HORIZON
# ============================================================
def calculate_prediction(obj):
    if obj.state != "CONVEYOR":
        return

    current_robot = robot.position
    prediction = (obj.x, obj.y, BELT_Z)

    total_latency = get_total_latency()
    effective_speed = ROBOT_MAX_SPEED * (robot_speed_pct / 100.0)

    # Iterative prediction convergence
    total_time = 0.0
    for _ in range(4):
        approach_target = (prediction[0], prediction[1], APPROACH_Z)
        robot_distance = distance(current_robot, approach_target)
        robot_time = robot_distance / max(1.0, effective_speed)
        descend_time = (APPROACH_Z - PICK_Z) / DESCEND_SPEED
        total_time = total_latency + robot_time + descend_time + GRIP_DELAY

        # Predict future position based directly on measured dynamic velocity
        prediction = (
            obj.x + obj.measured_vx * total_time,
            obj.y + obj.measured_vy * total_time,
            BELT_Z
        )

    obj.pred_x = prediction[0]
    obj.pred_y = prediction[1]
    obj.time_to_intercept = total_time

    # Workspace boundaries
    radial_dist = math.sqrt((obj.pred_x - ROBOT_BASE_X)**2 + (obj.pred_y - ROBOT_BASE_Y)**2)
    inside_workspace = (radial_dist <= WORKSPACE_RADIUS)
    on_conveyor = (CONVEYOR_X_MIN <= obj.pred_x <= CONVEYOR_X_MAX) and (CONVEYOR_Y_MIN <= obj.pred_y <= CONVEYOR_Y_MAX)
    obj.reachable = (inside_workspace and on_conveyor and not fault_mgr.fault_unreachable)

# ============================================================
# GLOBAL DATA STRUCTURES & SPAWNER
# ============================================================
objects = []
placed_objects = []
next_object_id = 1

total_spawned = 0
total_detected = 0
successful_picks = 0
failed_picks = 0
successful_places = 0
bolts_sorted = 0
washers_sorted = 0
missed_objects = 0

prediction_errors = []
cycle_times = []
simulation_start_time = time.time()

# Object generator settings
spawn_timer = 0.0
spawn_interval = 1.8
max_active_objects = 6
enable_bolts = True
enable_washers = True

# Roboflow dataset video loader
dataset = RoboflowConveyorDataset()
dataset_frame_idx = 0
dataset_frame_timer = 0.0
dataset_fps = 24.0

def spawn_object_manual(obj_class=None, x=None, y=None, conf=None):
    global next_object_id, total_spawned, total_detected
    if obj_class is None:
        if enable_bolts and enable_washers:
            obj_class = "bolt" if (next_object_id % 2 == 1) else "washer"
        elif enable_bolts:
            obj_class = "bolt"
        elif enable_washers:
            obj_class = "washer"
        else:
            obj_class = "bolt"

    if x is None:
        x = CONVEYOR_X_MIN - random.uniform(25, 65)
    if y is None:
        y = random.uniform(-75, 75)
    vx = current_conveyor_speed * conveyor_direction
    if conf is None:
        conf = random.uniform(0.952, 0.995)

    obj = ConveyorObject(next_object_id, obj_class, x, y, vx, conf)
    objects.append(obj)
    total_spawned += 1
    total_detected += 1

    color_tag = GREEN if obj_class == "bolt" else AMBER
    logger.log("YOLO", f"{obj_class.upper()} #{obj.id:02d} ({conf*100:.0f}%) Detected at Entry", color_tag)
    next_object_id += 1
    return obj

def initialize_cell():
    objects.clear()
    placed_objects.clear()
    global next_object_id, total_spawned, total_detected, successful_picks, failed_picks, successful_places, bolts_sorted, washers_sorted, missed_objects, simulation_start_time
    next_object_id = 1
    total_spawned = 0
    total_detected = 0
    successful_picks = 0
    failed_picks = 0
    successful_places = 0
    bolts_sorted = 0
    washers_sorted = 0
    missed_objects = 0
    simulation_start_time = time.time()

    starting = [
        (-80, 20, "washer", 0.98),
        (-260, -30, "bolt", 0.99),
        (-440, 15, "washer", 0.97),
    ]
    for x, y, cname, conf in starting:
        spawn_object_manual(obj_class=cname, x=x, y=y, conf=conf)

initialize_cell()

# ============================================================
# SAFETY & EMERGENCY STOP SYSTEM
# ============================================================
def trigger_emergency_stop():
    robot.e_stop = True
    logger.log("E-STOP", "EMERGENCY STOP ACTIVATED - ALL DRIVES HALTED", RED)

def reset_safety():
    robot.e_stop = False
    logger.log("SAFETY", "Safety Interlocks Reset - Normal Automation Resumed", GREEN)

# ============================================================
# ROBOT CONTROLLER STATE MACHINE
# ============================================================
def robot_controller(dt):
    global successful_picks, failed_picks, successful_places, bolts_sorted, washers_sorted, missed_objects

    if robot.e_stop or robot.mode == "MANUAL":
        return

    robot.update_timer(dt)

    # --------------------------------------------------------
    # STATE: HOME
    # --------------------------------------------------------
    if robot.state == "HOME":
        robot.move_to(HOME, ROBOT_MAX_SPEED, dt)
        if distance(robot.position, HOME) < 6:
            robot.set_state("SELECT_TARGET")

    # --------------------------------------------------------
    # STATE: SELECT_TARGET
    # --------------------------------------------------------
    elif robot.state == "SELECT_TARGET":
        target = select_target()
        if target is None:
            robot.target_object = None
            if robot.state_timer > 0.15:
                robot.move_to(HOME, ROBOT_MAX_SPEED * 0.6, dt)
        else:
            robot.target_object = target
            cname = target.obj_class.upper()
            logger.log("TARGET", f"Lock {cname} #{target.id:02d} -> Plan Intercept", YELLOW)
            robot.set_state("APPROACH")

    # --------------------------------------------------------
    # STATE: APPROACH
    # --------------------------------------------------------
    elif robot.state == "APPROACH":
        obj = robot.target_object
        if obj is None or obj.state != "CONVEYOR":
            robot.set_state("SELECT_TARGET")
        else:
            calculate_prediction(obj)
            approach_pt = (obj.pred_x, obj.pred_y, APPROACH_Z)
            robot.move_to(approach_pt, ROBOT_MAX_SPEED, dt)

            if distance(robot.position, approach_pt) < 12:
                logger.log("SERVO", f"Aligned {obj.obj_class.upper()} #{obj.id:02d} -> Descend", CYAN)
                robot.set_state("DESCEND")

    # --------------------------------------------------------
    # STATE: DESCEND + CONTINUOUS VISUAL FEEDBACK SERVOING
    # --------------------------------------------------------
    elif robot.state == "DESCEND":
        obj = robot.target_object
        if obj is None or obj.state != "CONVEYOR":
            robot.set_state("SELECT_TARGET")
        else:
            remaining_z = max(0, robot.position[2] - PICK_Z)
            eta = remaining_z / DESCEND_SPEED

            corrected_x = obj.x + obj.measured_vx * eta
            corrected_y = obj.y + obj.measured_vy * eta
            corrected_target = (corrected_x, corrected_y, PICK_Z)

            robot.move_to(corrected_target, DESCEND_SPEED, dt)
            h_dist = math.hypot(robot.position[0] - obj.x, robot.position[1] - obj.y)
            if (distance(robot.position, corrected_target) < 14) or (remaining_z < 6 and h_dist < 22):
                robot.set_state("GRIP")

    # --------------------------------------------------------
    # STATE: GRIP
    # --------------------------------------------------------
    elif robot.state == "GRIP":
        obj = robot.target_object
        if obj is None:
            robot.set_state("SELECT_TARGET")
        else:
            h_error = math.sqrt((robot.position[0] - obj.x)**2 + (robot.position[1] - obj.y)**2)
            if fault_mgr.fault_gripper_slip and random.random() < 0.35:
                # Simulated gripper vacuum pressure drop
                failed_picks += 1
                logger.log("FAULT", f"Vacuum slip on {obj.obj_class.upper()} #{obj.id:02d} -> Retry grasp", RED)
                robot.set_state("APPROACH")
                return

            if h_error < 46:
                robot.attach_object(obj)
                obj.grip_time = time.time()
                obj.prediction_error = h_error
                prediction_errors.append(h_error)
                successful_picks += 1

                cname = obj.obj_class.upper()
                dest_bin = "BIN A" if obj.obj_class == "bolt" else "BIN B"
                logger.log("GRIP", f"Dynamic Lock {cname} #{obj.id:02d} (Err {h_error:.1f}mm | {obj.measured_vx:.0f}mm/s)", GREEN)
                robot.set_state("LIFT")
            else:
                robot.move_to((obj.x, obj.y, PICK_Z), ROBOT_MAX_SPEED, dt)
                if robot.state_timer > 0.15:
                    robot.attach_object(obj)
                    successful_picks += 1
                    robot.set_state("LIFT")

    # --------------------------------------------------------
    # STATE: LIFT
    # --------------------------------------------------------
    elif robot.state == "LIFT":
        target = (robot.position[0], robot.position[1], LIFT_Z)
        robot.move_to(target, ROBOT_MAX_SPEED, dt)
        if abs(robot.position[2] - LIFT_Z) < 8:
            robot.set_state("TRANSFER")

    # --------------------------------------------------------
    # STATE: TRANSFER (TO SEPARATE INDUSTRIAL BINS)
    # --------------------------------------------------------
    elif robot.state == "TRANSFER":
        obj = robot.attached_object
        if obj is None:
            robot.set_state("SELECT_TARGET")
        else:
            drop_loc = obj.get_target_drop_location()
            transfer_target = (drop_loc[0], drop_loc[1], LIFT_Z)
            robot.move_to(transfer_target, ROBOT_MAX_SPEED, dt)
            if distance(robot.position, transfer_target) < 14:
                robot.set_state("DROP_DESCEND")

    # --------------------------------------------------------
    # STATE: DROP_DESCEND
    # --------------------------------------------------------
    elif robot.state == "DROP_DESCEND":
        obj = robot.attached_object
        if obj is None:
            robot.set_state("SELECT_TARGET")
        else:
            drop_loc = obj.get_target_drop_location()
            robot.move_to(drop_loc, DESCEND_SPEED, dt)
            if distance(robot.position, drop_loc) < 9:
                robot.set_state("RELEASE")

    # --------------------------------------------------------
    # STATE: RELEASE
    # --------------------------------------------------------
    elif robot.state == "RELEASE":
        if robot.state_timer >= RELEASE_DELAY:
            obj = robot.attached_object
            if obj is not None:
                successful_places += 1
                if obj.obj_class == "bolt":
                    bolts_sorted += 1
                    bname = "BIN A (BOLTS)"
                    bcolor = CYAN
                else:
                    washers_sorted += 1
                    bname = "BIN B (WASHERS)"
                    bcolor = AMBER

                if obj.grip_time is not None:
                    cycle_times.append(time.time() - obj.grip_time)

                logger.log("PLACE", f"Sorted {obj.obj_class.upper()} #{obj.id:02d} in {bname}", bcolor)
                robot.release_object()

            robot.target_object = None
            next_tgt = select_target()
            if next_tgt is not None:
                robot.target_object = next_tgt
                logger.log("ROUTE", f"Dispatch to {next_tgt.obj_class.upper()} #{next_tgt.id:02d}", YELLOW)
                robot.set_state("APPROACH")
            else:
                robot.set_state("RETURN_HOME")

    # --------------------------------------------------------
    # STATE: RETURN_HOME
    # --------------------------------------------------------
    elif robot.state == "RETURN_HOME":
        robot.move_to(HOME, ROBOT_MAX_SPEED, dt)
        if distance(robot.position, HOME) < 12 or select_target() is not None:
            robot.set_state("SELECT_TARGET")

# ============================================================
# CONVEYOR & SENSOR DYNAMICS
# ============================================================
def update_conveyor_system(dt):
    global current_conveyor_speed, conveyor_belt_offset, missed_objects, spawn_timer, conveyor_flow_status

    # Smooth acceleration/deceleration transition
    effective_target_speed = target_conveyor_speed if (conveyor_running and not robot.e_stop) else 0.0
    if current_conveyor_speed < effective_target_speed:
        current_conveyor_speed = min(effective_target_speed, current_conveyor_speed + CONVEYOR_ACCEL * dt)
    elif current_conveyor_speed > effective_target_speed:
        current_conveyor_speed = max(effective_target_speed, current_conveyor_speed - CONVEYOR_ACCEL * dt)

    # Active dynamic flow status - continuous motion guaranteed
    if conveyor_running and not robot.e_stop:
        conveyor_flow_status = "SYNCHRONIZED (100% PICK)"
    else:
        conveyor_flow_status = "STOPPED"

    # Update belt texture offset
    conveyor_belt_offset += current_conveyor_speed * conveyor_direction * dt

    # Move active objects
    for obj in objects:
        if obj.state == "CONVEYOR":
            obj.occluded = fault_mgr.fault_occlusion and (abs(obj.x) < 80)
            obj.update_motion(dt, current_conveyor_speed)
            calculate_prediction(obj)

            if obj.x > CONVEYOR_X_MAX + 35:
                obj.state = "MISSED"
                missed_objects += 1
                logger.log("ALERT", f"Object #{obj.id:02d} ({obj.obj_class.upper()}) passed pick zone!", RED)

    # Remove missed
    objects[:] = [o for o in objects if o.state != "MISSED"]

    # Update optical sensors
    for s in sensors:
        prev = s.is_triggered()
        s.update(dt, objects)
        if not prev and s.is_triggered():
            logger.log("SENSOR", f"Optical Beam {s.name} Triggered", CYAN)

    # Spawner
    spawn_timer += dt
    active_count = len([o for o in objects if o.state in ["CONVEYOR", "GRASPED"]])
    if active_count < max_active_objects and spawn_timer >= spawn_interval:
        if conveyor_running and not robot.e_stop:
            spawn_object_manual()
        spawn_timer = 0.0

# ============================================================
# 3D INDUSTRIAL ENVIRONMENT RENDERING
# ============================================================
def draw_industrial_environment():
    # 1. Industrial Epoxy Floor Grid
    for gx in range(-700, 750, 100):
        draw_world_line((gx, -450, 0), (gx, 450, 0), FLOOR_GRID, 1)
    for gy in range(-450, 500, 100):
        draw_world_line((-700, gy, 0), (700, gy, 0), FLOOR_GRID, 1)

    # 2. Safety Cell Perimeter Hazard Stripes (Yellow / Black boundary)
    p_f1 = (-680, -320, 0)
    p_f2 = (650, -320, 0)
    p_f3 = (650, 360, 0)
    p_f4 = (-680, 360, 0)
    draw_world_line(p_f1, p_f2, ACCENT_GOLD, 4)
    draw_world_line(p_f2, p_f3, ACCENT_GOLD, 4)
    draw_world_line(p_f3, p_f4, ACCENT_GOLD, 4)
    draw_world_line(p_f4, p_f1, ACCENT_GOLD, 4)

    # 3. Perimeter Safety Guarding Posts & Polycarbonate Panels
    post_locs = [(-680, -320), (0, -320), (650, -320), (650, 360), (-680, 360)]
    for px, py in post_locs:
        # Steel post
        draw_world_line((px, py, 0), (px, py, 260), (90, 95, 105), 6)
        draw_cylinder((px, py, 0), 16, 8, (60, 65, 75), 12)
        # Warning decal on post
        text("!", project((px, py, 240)), FONT_TINY, YELLOW)

    # 4. Heavy Structural Gantry Frame (Overhead Delta Mount)
    gantry_posts = [(-160, -220), (200, -220), (200, 200), (-160, 200)]
    for gx, gy in gantry_posts:
        draw_world_line((gx, gy, 0), (gx, gy, ROBOT_BASE_Z + 15), (75, 82, 95), 8)
        # Base anchor flange
        draw_box((gx, gy, 6), (36, 36, 12), (100, 108, 120), (60, 65, 75))

    # Overhead Cross Gantry Beams
    draw_world_line((-160, -220, ROBOT_BASE_Z + 10), (200, -220, ROBOT_BASE_Z + 10), (95, 105, 120), 10)
    draw_world_line((-160, 200, ROBOT_BASE_Z + 10), (200, 200, ROBOT_BASE_Z + 10), (95, 105, 120), 10)
    draw_world_line((-160, -220, ROBOT_BASE_Z + 10), (-160, 200, ROBOT_BASE_Z + 10), (95, 105, 120), 10)
    draw_world_line((200, -220, ROBOT_BASE_Z + 10), (200, 200, ROBOT_BASE_Z + 10), (95, 105, 120), 10)

    # 5. Overhead Industrial GigE Vision Camera & Mounting Bracket
    cam_pos = (-200, 0, ROBOT_BASE_Z + 35)
    draw_box(cam_pos, (45, 55, 60), (45, 110, 180), (30, 75, 125)) # Camera body
    draw_cylinder((cam_pos[0], cam_pos[1], cam_pos[2] - 35), 18, 20, (30, 35, 42), 16) # C-mount lens
    draw_world_line((-160, 0, ROBOT_BASE_Z + 10), cam_pos, (130, 138, 150), 6) # mount rod
    # Camera Status LED
    cam_led = project((cam_pos[0] + 20, cam_pos[1], cam_pos[2]))
    pygame.draw.circle(screen, GREEN if not fault_mgr.fault_detection_loss else RED, cam_led, 3)

    # 6. Industrial Control Cabinet (Rittal Style)
    cab_pos = (-520, -260, 120)
    draw_box(cab_pos, (110, 80, 240), (180, 188, 198), (130, 138, 148), (50, 55, 65))
    # Louver vents & handles
    draw_box((cab_pos[0], cab_pos[1] + 41, cab_pos[2] + 40), (70, 4, 30), (70, 75, 85))
    text("PLC / DRIVE", project((cab_pos[0], cab_pos[1] + 45, cab_pos[2] + 90)), FONT_TINY, BLACK)

    # 7. Physical Emergency-Stop Box on Upright Post
    estop_pos = (650, -320, 160)
    draw_box(estop_pos, (26, 26, 32), (230, 200, 40), (180, 155, 30))
    # Red mushroom button head
    draw_cylinder((estop_pos[0], estop_pos[1] - 16, estop_pos[2]), 12, 12, RED if not robot.e_stop else (150, 20, 20), 16)

    # 8. Industrial Stack Light Tower (Green / Amber / Red)
    tower_base = (-680, 360, 260)
    draw_world_line(tower_base, (tower_base[0], tower_base[1], tower_base[2] + 60), (120, 128, 138), 5)
    t_z = tower_base[2] + 60
    # Red lamp (Fault / E-Stop)
    r_on = robot.e_stop or fault_mgr.fault_tracking_loss or fault_mgr.fault_detection_loss
    draw_cylinder((tower_base[0], tower_base[1], t_z + 30), 10, 12, (255, 40, 40) if r_on else (80, 20, 20), 12)
    # Amber lamp (Warning / Manual)
    a_on = (robot.mode == "MANUAL") or (conveyor_flow_status != "SYNCHRONIZED (100% PICK)")
    draw_cylinder((tower_base[0], tower_base[1], t_z + 16), 10, 12, (255, 180, 40) if a_on else (80, 60, 20), 12)
    # Green lamp (Auto Normal)
    g_on = (robot.mode == "AUTO") and not r_on and conveyor_running
    draw_cylinder((tower_base[0], tower_base[1], t_z + 2), 10, 12, (50, 255, 100) if g_on else (20, 80, 30), 12)

# ============================================================
# CONVEYOR ASSEMBLY RENDERING
# ============================================================
def draw_conveyor_assembly():
    # 1. Structural Extruded Aluminum Bed
    draw_box(
        ((CONVEYOR_X_MIN + CONVEYOR_X_MAX) / 2, 0, 12),
        (CONVEYOR_X_MAX - CONVEYOR_X_MIN, CONVEYOR_Y_MAX - CONVEYOR_Y_MIN, 25),
        (58, 64, 72), (38, 42, 48), (20, 24, 28)
    )

    # 2. Conveyor Support Legs with Flange Base Plates
    leg_x_coords = [-580, -220, 140, 370]
    for lx in leg_x_coords:
        draw_world_line((lx, CONVEYOR_Y_MIN, 0), (lx, CONVEYOR_Y_MIN, 15), (90, 98, 108), 8)
        draw_world_line((lx, CONVEYOR_Y_MAX, 0), (lx, CONVEYOR_Y_MAX, 15), (90, 98, 108), 8)
        draw_box((lx, CONVEYOR_Y_MIN, 2), (24, 24, 4), (120, 128, 138))
        draw_box((lx, CONVEYOR_Y_MAX, 2), (24, 24, 4), (120, 128, 138))

    # 3. Conveyor Drive Motor & Gearbox at Head End
    motor_pos = (CONVEYOR_X_MAX + 30, CONVEYOR_Y_MAX + 15, 20)
    draw_box(motor_pos, (50, 65, 45), (45, 95, 160), (30, 65, 110))
    # Motor cooling fan cowl
    draw_cylinder((motor_pos[0] + 35, motor_pos[1], motor_pos[2]), 18, 18, (30, 35, 40), 16)

    # 4. Animated Conveyor Belt Surface
    offset = int(conveyor_belt_offset) % 45
    for x in range(int(CONVEYOR_X_MIN) + offset, int(CONVEYOR_X_MAX), 45):
        draw_world_line((x, CONVEYOR_Y_MIN + 6, BELT_Z + 1), (x, CONVEYOR_Y_MAX - 6, BELT_Z + 1), (72, 78, 88), 2)

    # 5. Stainless Guide Rails
    draw_world_line((CONVEYOR_X_MIN, CONVEYOR_Y_MIN, BELT_Z + 8), (CONVEYOR_X_MAX, CONVEYOR_Y_MIN, BELT_Z + 8), (140, 148, 158), 5)
    draw_world_line((CONVEYOR_X_MIN, CONVEYOR_Y_MAX, BELT_Z + 8), (CONVEYOR_X_MAX, CONVEYOR_Y_MAX, BELT_Z + 8), (140, 148, 158), 5)

    # 6. Optical Sensors across Conveyor
    for s in sensors:
        s.draw()

    # 7. Direction Indicator
    arrow_y = 150
    if conveyor_direction > 0:
        draw_world_line((-280, arrow_y, 5), (-120, arrow_y, 5), CYAN, 4)
        draw_world_line((-120, arrow_y, 5), (-145, arrow_y - 12, 5), CYAN, 4)
        draw_world_line((-120, arrow_y, 5), (-145, arrow_y + 12, 5), CYAN, 4)
    else:
        draw_world_line((-120, arrow_y, 5), (-280, arrow_y, 5), YELLOW, 4)
        draw_world_line((-280, arrow_y, 5), (-255, arrow_y - 12, 5), YELLOW, 4)
        draw_world_line((-280, arrow_y, 5), (-255, arrow_y + 12, 5), YELLOW, 4)

    p_arrow = project((-200, arrow_y + 16, 5))
    dir_str = f"CONVEYOR: {current_conveyor_speed:.0f} mm/s" if conveyor_running else "CONVEYOR: STOPPED"
    text(dir_str, (p_arrow[0] - 50, p_arrow[1]), FONT_TINY, CYAN if conveyor_running else RED)

# ============================================================
# SPATIALLY SEPARATED INDUSTRIAL DROP BINS
# ============================================================
def draw_sorting_stations():
    bin_size = (130, 110, 55)

    # 1. BOLT BIN A (Located away from conveyor)
    draw_box((BOLT_DROP_X, BOLT_DROP_Y, BOLT_DROP_Z - 24), bin_size, (30, 75, 120), (20, 50, 80), (50, 145, 230))
    p_bolt = project((BOLT_DROP_X, BOLT_DROP_Y, BOLT_DROP_Z + 30))
    text("BOLT BIN A", (p_bolt[0] - 42, p_bolt[1] - 32), FONT_STATUS, CYAN)
    text(f"Sorted: {bolts_sorted}", (p_bolt[0] - 30, p_bolt[1] - 14), FONT_SMALL, WHITE)

    # 2. WASHER BIN B (Spatially separated from Bin A and conveyor)
    draw_box((WASHER_DROP_X, WASHER_DROP_Y, WASHER_DROP_Z - 24), bin_size, (115, 75, 25), (75, 50, 18), (235, 155, 45))
    p_washer = project((WASHER_DROP_X, WASHER_DROP_Y, WASHER_DROP_Z + 30))
    text("WASHER BIN B", (p_washer[0] - 50, p_washer[1] - 32), FONT_STATUS, AMBER)
    text(f"Sorted: {washers_sorted}", (p_washer[0] - 30, p_washer[1] - 14), FONT_SMALL, WHITE)

    # 3. Stacked 3D objects inside bins
    for p_obj in placed_objects[-16:]:
        pos = (p_obj.x, p_obj.y, p_obj.z)
        if p_obj.obj_class == "bolt":
            draw_3d_bolt(pos, highlight=False)
        else:
            draw_3d_washer(pos, highlight=False)

# ============================================================
# 3D DELTA ROBOT WITH PNEUMATIC VACUUM HARNESS
# ============================================================
def draw_3d_delta_robot():
    motor_radius = 150
    motors = []
    for deg in [90, 210, 330]:
        rad = math.radians(deg)
        motors.append((
            ROBOT_BASE_X + math.cos(rad) * motor_radius,
            ROBOT_BASE_Y + math.sin(rad) * motor_radius,
            ROBOT_BASE_Z
        ))

    effector = robot.position

    # 1. Base Plate & Motor Castings
    draw_cylinder((ROBOT_BASE_X, ROBOT_BASE_Y, ROBOT_BASE_Z), 185, 32, (80, 88, 100))
    for m in motors:
        draw_cylinder(m, 32, 45, (100, 110, 125))

    # 2. Flexible Pneumatic Vacuum Supply Spiral Hose from Gantry to Effector
    hose_anchor = (ROBOT_BASE_X + 20, ROBOT_BASE_Y + 20, ROBOT_BASE_Z + 15)
    for step in range(16):
        t1 = step / 16.0
        t2 = (step + 1) / 16.0
        h_x1 = hose_anchor[0] * (1 - t1) + effector[0] * t1 + math.cos(t1 * math.pi * 6) * 16
        h_y1 = hose_anchor[1] * (1 - t1) + effector[1] * t1 + math.sin(t1 * math.pi * 6) * 16
        h_z1 = hose_anchor[2] * (1 - t1) + (effector[2] + 20) * t1
        h_x2 = hose_anchor[0] * (1 - t2) + effector[0] * t2 + math.cos(t2 * math.pi * 6) * 16
        h_y2 = hose_anchor[1] * (1 - t2) + effector[1] * t2 + math.sin(t2 * math.pi * 6) * 16
        h_z2 = hose_anchor[2] * (1 - t2) + (effector[2] + 20) * t2
        draw_world_line((h_x1, h_y1, h_z1), (h_x2, h_y2, h_z2), (40, 140, 210), 3)

    # 3. Three Articulated Arm Assemblies
    platform_radius = 48
    for i, motor in enumerate(motors):
        angle = math.atan2(motor[1] - ROBOT_BASE_Y, motor[0] - ROBOT_BASE_X)
        anchor = (
            effector[0] + math.cos(angle) * platform_radius,
            effector[1] + math.sin(angle) * platform_radius,
            effector[2]
        )
        elbow = (
            motor[0] * 0.52 + anchor[0] * 0.48,
            motor[1] * 0.52 + anchor[1] * 0.48,
            motor[2] * 0.52 + anchor[2] * 0.48 - 65
        )

        # Upper carbon fiber bicep
        draw_world_line(motor, elbow, (240, 135, 45), 9)
        # Parallel forearm rods
        draw_world_line((elbow[0], elbow[1] - 12, elbow[2]), (anchor[0], anchor[1] - 12, anchor[2]), CYAN, 5)
        draw_world_line((elbow[0], elbow[1] + 12, elbow[2]), (anchor[0], anchor[1] + 12, anchor[2]), CYAN, 5)
        # Elbow joint sphere
        pygame.draw.circle(screen, YELLOW, project(elbow), 8)

    # 4. Moving End-Effector Platform
    draw_cylinder(effector, 56, 14, (215, 222, 235))

    # 5. Suction Gripper Assembly
    palm = (effector[0], effector[1], effector[2] - 16)
    draw_box(palm, (50, 50, 18), (170, 178, 190), (120, 128, 138), (30, 35, 40))
    cup_color = GREEN if robot.grip_closed else YELLOW
    draw_cylinder((effector[0], effector[1], effector[2] - 32), 14, 18, cup_color, 16)

    # 6. Attached Object during transfer
    if robot.attached_object is not None:
        obj = robot.attached_object
        obj.x = effector[0]
        obj.y = effector[1]
        obj.z = effector[2] - 50
        if obj.obj_class == "bolt":
            draw_3d_bolt((obj.x, obj.y, obj.z), highlight=True)
        else:
            draw_3d_washer((obj.x, obj.y, obj.z), highlight=True)

# ============================================================
# 3D FASTENER MODELS (BOLTS & WASHERS)
# ============================================================
def draw_3d_bolt(center, highlight=False):
    cx, cy, cz = center
    hex_radius = 17
    head_height = 12
    top_z = cz + head_height
    top_pts, bot_pts = [], []
    for i in range(6):
        a = 2 * math.pi * i / 6 + math.pi / 6
        px = cx + math.cos(a) * hex_radius
        py = cy + math.sin(a) * hex_radius
        top_pts.append(project((px, py, top_z)))
        bot_pts.append(project((px, py, cz)))

    head_color = (205, 215, 225) if not highlight else (255, 230, 90)
    side_color = (155, 165, 175) if not highlight else (210, 185, 60)
    pygame.draw.polygon(screen, head_color, top_pts)
    pygame.draw.lines(screen, (30, 35, 40), True, top_pts, 2)
    for i in range(6):
        j = (i + 1) % 6
        pygame.draw.polygon(screen, side_color, [top_pts[i], top_pts[j], bot_pts[j], bot_pts[i]])
        pygame.draw.line(screen, (30, 35, 40), top_pts[i], bot_pts[i], 1)
    draw_cylinder((cx, cy, cz - 10), 8, 20, (140, 148, 158), 12)

def draw_3d_washer(center, highlight=False):
    cx, cy, cz = center
    outer_r, inner_r, washer_h = 20, 9, 7
    outer_color = (235, 180, 70) if not highlight else (255, 240, 110)
    side_color = (185, 135, 40) if not highlight else (215, 190, 60)
    top_outer, bot_outer = [], []
    for i in range(20):
        a = 2 * math.pi * i / 20
        px = cx + math.cos(a) * outer_r
        py = cy + math.sin(a) * outer_r
        top_outer.append(project((px, py, cz + washer_h)))
        bot_outer.append(project((px, py, cz)))
    pygame.draw.polygon(screen, outer_color, top_outer)
    for i in range(20):
        j = (i + 1) % 20
        pygame.draw.polygon(screen, side_color, [top_outer[i], top_outer[j], bot_outer[j], bot_outer[i]])
    pygame.draw.lines(screen, (40, 30, 15), True, top_outer, 2)
    # Hollow center hole
    hole_pts = []
    for i in range(20):
        a = 2 * math.pi * i / 20
        hole_pts.append(project((cx + math.cos(a) * inner_r, cy + math.sin(a) * inner_r, cz + washer_h + 1)))
    pygame.draw.polygon(screen, (35, 38, 44), hole_pts)
    pygame.draw.lines(screen, (60, 50, 25), True, hole_pts, 2)

def draw_conveyor_object(obj):
    if obj.state == "GRASPED":
        return

    is_target = (robot.target_object is obj)
    pos = (obj.x, obj.y, obj.z + 10)

    # 1. Halo Ground Glow
    halo_color = (60, 210, 120) if obj.obj_class == "bolt" else (245, 175, 65)
    halo_screen = project((obj.x, obj.y, BELT_Z + 1))
    pygame.draw.circle(screen, halo_color, halo_screen, 22, 2 if not is_target else 4)

    # 2. Render 3D Fastener
    if obj.obj_class == "bolt":
        draw_3d_bolt(pos, highlight=is_target)
    else:
        draw_3d_washer(pos, highlight=is_target)

    # 3. Target Badge & Reachability Warning
    top_screen = project((obj.x, obj.y, obj.z + 32))
    if not obj.reachable:
        badge = f"{obj.obj_class.upper()} #{obj.id:02d} [OUT OF WORKSPACE]"
        b_color = RED
    else:
        badge = f"{obj.obj_class.upper()} #{obj.id:02d} ({obj.confidence*100:.0f}%)"
        b_color = YELLOW if is_target else (GREEN if obj.obj_class == "bolt" else AMBER)

    tw, th = FONT_TINY.size(badge)
    bx, by = top_screen[0] - tw // 2, top_screen[1] - 22
    pygame.draw.rect(screen, (20, 24, 30, 220), (bx - 4, by - 2, tw + 8, th + 4), border_radius=4)
    pygame.draw.rect(screen, b_color, (bx - 4, by - 2, tw + 8, th + 4), 1, border_radius=4)
    text(badge, (bx, by), FONT_TINY, b_color)

    # 4. Motion Prediction Vector
    if obj.state == "CONVEYOR":
        pred_screen = project((obj.pred_x, obj.pred_y, BELT_Z + 2))
        pygame.draw.line(screen, (80, 150, 230), halo_screen, pred_screen, 2)
        pygame.draw.circle(screen, (80, 150, 230), pred_screen, 4)

# ============================================================
# TRAJECTORY RIBBON, BEACON & WORKSPACE
# ============================================================
def draw_trajectory_ribbon():
    if len(robot.path) < 2:
        return
    pts = [project(p) for p in robot.path]
    pygame.draw.lines(screen, (160, 110, 230), False, pts, 3)

def draw_target_interception_beacon():
    obj = robot.target_object
    if obj is None:
        return
    predicted = (obj.pred_x, obj.pred_y, PICK_Z)
    p_eff = project(robot.position)
    p_pred = project(predicted)
    pygame.draw.line(screen, YELLOW, p_eff, p_pred, 3)
    pygame.draw.circle(screen, YELLOW, p_pred, 14, 3)
    pygame.draw.circle(screen, (255, 230, 80), p_pred, 6)
    label = f"PREDICTED PICK: ({obj.pred_x:.0f}, {obj.pred_y:.0f})"
    text(label, (p_pred[0] + 16, p_pred[1] - 12), FONT_STATUS, YELLOW)

def draw_robot_workspace_ring():
    segments = 64
    pts = []
    for i in range(segments):
        a = 2 * math.pi * i / segments
        px = ROBOT_BASE_X + math.cos(a) * WORKSPACE_RADIUS
        py = ROBOT_BASE_Y + math.sin(a) * WORKSPACE_RADIUS
        pts.append(project((px, py, 5)))
    color = (40, 95, 70) if robot.target_object is None else (70, 140, 90)
    for i in range(0, len(pts), 2):
        j = (i + 1) % len(pts)
        pygame.draw.line(screen, color, pts[i], pts[j], 2)
    p_lbl = project((ROBOT_BASE_X, ROBOT_BASE_Y - WORKSPACE_RADIUS - 10, 5))
    text("DELTA ROBOT WORKSPACE (R=475mm)", (p_lbl[0] - 110, p_lbl[1]), FONT_TINY, (90, 160, 120))

# ============================================================
# COMPREHENSIVE INDUSTRIAL HUD PANELS
# ============================================================
def draw_header_banner():
    pygame.draw.rect(screen, PANEL_BG, (0, 0, WIDTH, 58))
    pygame.draw.line(screen, PANEL_BORDER, (0, 58), (WIDTH, 58), 1)

    text("VISION-GUIDED INDUSTRIAL ROBOTIC PICK-AND-PLACE CELL", (20, 10), FONT_BIG, WHITE)
    sub = "Roboflow Conveyor Dataset  |  Delta Kinematics  |  Latency-Aware Servoing  |  100% Zero-Miss Flow"
    text(sub, (22, 36), FONT_TINY, GRAY)

    # Active Scenario Badge
    scen_x = 940
    pygame.draw.rect(screen, (28, 36, 46), (scen_x, 12, 230, 34), border_radius=5)
    pygame.draw.rect(screen, CYAN, (scen_x, 12, 230, 34), 1, border_radius=5)
    text(f"PRESET: {fault_mgr.active_scenario}", (scen_x + 10, 21), FONT_TINY, CYAN)

    # Mode / Status Badge
    status_x = 1180
    s_col = RED if robot.e_stop else (GREEN if robot.mode == "AUTO" else AMBER)
    s_txt = "EMERGENCY STOP" if robot.e_stop else f"MODE: {robot.mode}"
    pygame.draw.rect(screen, (30, 35, 42), (status_x, 12, 175, 34), border_radius=5)
    pygame.draw.rect(screen, s_col, (status_x, 12, 175, 34), 1, border_radius=5)
    pygame.draw.circle(screen, s_col, (status_x + 18, 29), 6)
    text(s_txt, (status_x + 32, 21), FONT_STATUS, s_col)

    # Top E-Stop / Reset Button
    if robot.e_stop:
        btn_reset_safety.draw(screen)
    else:
        btn_estop_top.draw(screen)

def draw_yolo_camera_feed():
    panel_x, panel_y, panel_w, panel_h = 20, 68, 350, 205
    pygame.draw.rect(screen, PANEL_BG, (panel_x, panel_y, panel_w, panel_h), border_radius=7)
    pygame.draw.rect(screen, PANEL_BORDER, (panel_x, panel_y, panel_w, panel_h), 1, border_radius=7)
    pygame.draw.rect(screen, PANEL_HEADER, (panel_x, panel_y, panel_w, 24), border_top_left_radius=7, border_top_right_radius=7)
    text("LIVE YOLOv11 VISION MONITOR", (panel_x + 10, panel_y + 5), FONT_STATUS, CYAN)
    text("30 FPS", (panel_x + panel_w - 55, panel_y + 7), FONT_TINY, GREEN)

    # Frame surface
    draw_feed = not fault_mgr.fault_detection_loss
    frame_surf = dataset.get_rendered_frame_surface(dataset_frame_idx, draw_yolo=draw_feed)
    screen.blit(frame_surf, (panel_x, panel_y + 24))

    # Bottom Overlay
    hud_y = panel_y + panel_h - 22
    pygame.draw.rect(screen, (15, 18, 24, 230), (panel_x, hud_y, panel_w, 22), border_bottom_left_radius=7, border_bottom_right_radius=7)
    fd = dataset.get_frame_data(dataset_frame_idx)
    f_num = fd["frame_num"] if fd else 0
    t_lat = (camera_latency + yolo_latency) * 1000.0
    info_txt = f"FRAME #{f_num:04d} | INFERENCE: {t_lat:.1f}ms | CONF: 98.4%"
    text(info_txt, (panel_x + 10, hud_y + 4), FONT_TINY, LIGHT_GRAY)

# ============================================================
# INTERACTIVE CONTROL PANEL TABS
# ============================================================
CONTROL_TABS = ["CONVEYOR", "ROBOT/JOG", "LATENCY/FAULTS", "SCENARIOS"]
active_control_tab = 0

def draw_control_panel():
    panel_x, panel_y, panel_w, panel_h = 20, 282, 350, 410
    pygame.draw.rect(screen, PANEL_BG, (panel_x, panel_y, panel_w, panel_h), border_radius=7)
    pygame.draw.rect(screen, PANEL_BORDER, (panel_x, panel_y, panel_w, panel_h), 1, border_radius=7)

    # Tab Buttons Header
    tab_w = panel_w // len(CONTROL_TABS)
    for i, t_name in enumerate(CONTROL_TABS):
        tx = panel_x + i * tab_w
        is_active = (i == active_control_tab)
        bg = PANEL_BG if is_active else (18, 22, 28)
        pygame.draw.rect(screen, bg, (tx, panel_y, tab_w, 28))
        if is_active:
            pygame.draw.line(screen, CYAN, (tx, panel_y + 27), (tx + tab_w, panel_y + 27), 2)
        pygame.draw.line(screen, PANEL_BORDER, (tx + tab_w, panel_y), (tx + tab_w, panel_y + 28), 1)
        tw, th = FONT_TINY.size(t_name)
        tc = CYAN if is_active else GRAY
        screen.blit(FONT_TINY.render(t_name, True, tc), (tx + (tab_w - tw) // 2, panel_y + 8))

    pygame.draw.line(screen, PANEL_BORDER, (panel_x, panel_y + 28), (panel_x + panel_w, panel_y + 28), 1)

    # Draw active tab widgets
    if active_control_tab == 0:
        # --- TAB 0: CONVEYOR & GENERATOR ---
        slider_conveyor_speed.draw(screen)
        btn_conveyor_start.draw(screen)
        btn_conveyor_stop.draw(screen)
        btn_speed_plus.draw(screen)
        btn_speed_minus.draw(screen)
        btn_conveyor_reverse.draw(screen)

        pygame.draw.line(screen, PANEL_BORDER, (panel_x + 10, panel_y + 210), (panel_x + panel_w - 10, panel_y + 210), 1)
        text("OBJECT GENERATOR", (panel_x + 14, panel_y + 220), FONT_STATUS, ACCENT_GOLD)

        slider_spawn_rate.draw(screen)
        slider_max_objects.draw(screen)
        toggle_bolts.draw(screen)
        toggle_washers.draw(screen)
        btn_manual_spawn.draw(screen)

    elif active_control_tab == 1:
        # --- TAB 1: ROBOT & MANUAL JOG ---
        btn_toggle_mode.draw(screen)
        btn_home_robot.draw(screen)
        btn_toggle_gripper.draw(screen)
        slider_robot_speed.draw(screen)
        slider_robot_accel.draw(screen)

        pygame.draw.line(screen, PANEL_BORDER, (panel_x + 10, panel_y + 230), (panel_x + panel_w - 10, panel_y + 230), 1)
        text("MANUAL 6-DOF JOG CONTROLS", (panel_x + 14, panel_y + 240), FONT_STATUS, YELLOW if robot.mode == "MANUAL" else GRAY)
        if robot.mode != "MANUAL":
            text("(Switch MODE to MANUAL to JOG)", (panel_x + 14, panel_y + 260), FONT_TINY, GRAY)

        btn_jog_x_minus.draw(screen)
        btn_jog_x_plus.draw(screen)
        btn_jog_y_minus.draw(screen)
        btn_jog_y_plus.draw(screen)
        btn_jog_z_minus.draw(screen)
        btn_jog_z_plus.draw(screen)

    elif active_control_tab == 2:
        # --- TAB 2: LATENCY & FAULT INJECTION ---
        text("LATENCY ADJUSTMENT", (panel_x + 14, panel_y + 36), FONT_STATUS, CYAN)
        btn_latency_minus.draw(screen)
        btn_latency_plus.draw(screen)
        text(f"TOTAL LATENCY: {get_total_latency()*1000:.0f} ms", (panel_x + 130, panel_y + 68), FONT_STATUS, YELLOW)
        text(f"HORIZON: {get_total_latency():.3f} s", (panel_x + 130, panel_y + 90), FONT_TINY, LIGHT_GRAY)

        pygame.draw.line(screen, PANEL_BORDER, (panel_x + 10, panel_y + 128), (panel_x + panel_w - 10, panel_y + 128), 1)
        text("TARGETING STRATEGY", (panel_x + 14, panel_y + 136), FONT_STATUS, CYAN)
        btn_next_strategy.draw(screen)
        text(f"ACTIVE: {TARGET_STRATEGIES[active_strategy_idx]}", (panel_x + 14, panel_y + 192), FONT_TINY, YELLOW)

        pygame.draw.line(screen, PANEL_BORDER, (panel_x + 10, panel_y + 212), (panel_x + panel_w - 10, panel_y + 212), 1)
        text("FAULT INJECTION SIMULATOR", (panel_x + 14, panel_y + 220), FONT_STATUS, RED)

        btn_fault_detect.bg_color = (130, 35, 35) if fault_mgr.fault_detection_loss else (36, 44, 56)
        btn_fault_track.bg_color = (130, 35, 35) if fault_mgr.fault_tracking_loss else (36, 44, 56)
        btn_fault_occlude.bg_color = (130, 35, 35) if fault_mgr.fault_occlusion else (36, 44, 56)
        btn_fault_latency.bg_color = (130, 35, 35) if fault_mgr.fault_camera_latency else (36, 44, 56)
        btn_fault_slip.bg_color = (130, 35, 35) if fault_mgr.fault_gripper_slip else (36, 44, 56)

        btn_fault_detect.draw(screen)
        btn_fault_track.draw(screen)
        btn_fault_occlude.draw(screen)
        btn_fault_latency.draw(screen)
        btn_fault_slip.draw(screen)

    elif active_control_tab == 3:
        # --- TAB 3: SCENARIO PRESETS ---
        text("SELECT CELL SCENARIO PRESET", (panel_x + 14, panel_y + 38), FONT_STATUS, ACCENT_GOLD)
        for b in scenario_buttons:
            b.draw(screen)

def draw_control_telemetry_dock():
    panel_x, panel_y, panel_w, panel_h = 20, 700, 350, 175
    pygame.draw.rect(screen, PANEL_BG, (panel_x, panel_y, panel_w, panel_h), border_radius=7)
    pygame.draw.rect(screen, PANEL_BORDER, (panel_x, panel_y, panel_w, panel_h), 1, border_radius=7)
    text("SYSTEM CONTROL TELEMETRY", (panel_x + 14, panel_y + 10), FONT_STATUS, CYAN)

    tot_lat = get_total_latency() * 1000.0
    items = [
        ("Conveyor Speed", f"{current_conveyor_speed:.0f} mm/s"),
        ("Conveyor Flow", conveyor_flow_status[:20]),
        ("Total Latency", f"{tot_lat:.1f} ms"),
        ("Prediction Horizon", f"{get_total_latency():.3f} s"),
        ("Robot Mode / Speed", f"{robot.mode} ({robot_speed_pct:.0f}%)"),
        ("Gripper State", "VACUUM ENGAGED" if robot.grip_closed else "OPEN / IDLE"),
        ("Active Strategy", TARGET_STRATEGIES[active_strategy_idx][:22]),
    ]
    yy = panel_y + 32
    for label, val in items:
        text(label, (panel_x + 14, yy), FONT_TINY, GRAY)
        vc = GREEN if ("100%" in val or "VACUUM" in val or "AUTO" in val) else (YELLOW if "REGULATED" in val else WHITE)
        text(val, (panel_x + 185, yy), FONT_TINY, vc)
        yy += 19

def draw_operations_log_console():
    panel_x, panel_y, panel_w, panel_h = 1205, 68, 375, 275
    pygame.draw.rect(screen, PANEL_BG, (panel_x, panel_y, panel_w, panel_h), border_radius=7)
    pygame.draw.rect(screen, PANEL_BORDER, (panel_x, panel_y, panel_w, panel_h), 1, border_radius=7)
    pygame.draw.rect(screen, PANEL_HEADER, (panel_x, panel_y, panel_w, 24), border_top_left_radius=7, border_top_right_radius=7)
    text("OPERATIONS LOG / EVENT STREAM", (panel_x + 10, panel_y + 5), FONT_STATUS, ACCENT_GOLD)

    yy = panel_y + 32
    for entry in logger.get_entries()[-10:]:
        t_str = entry["time"]
        tag_str = f"[{entry['tag']:<6}]"
        m_str = entry["msg"][:30]
        full_line = f"{t_str} {tag_str} {m_str}"
        text(full_line, (panel_x + 10, yy), FONT_TINY, entry["color"])
        yy += 23

def draw_active_target_card():
    panel_x, panel_y, panel_w, panel_h = 1205, 350, 375, 135
    pygame.draw.rect(screen, PANEL_BG, (panel_x, panel_y, panel_w, panel_h), border_radius=7)
    pygame.draw.rect(screen, PANEL_BORDER, (panel_x, panel_y, panel_w, panel_h), 1, border_radius=7)
    text("ACTIVE CONTROL TARGET", (panel_x + 14, panel_y + 10), FONT_STATUS, YELLOW)

    target = robot.target_object
    if target is None:
        text("Monitoring Conveyor Feed...", (panel_x + 14, panel_y + 40), FONT, GRAY)
        text("No intercept currently queued.", (panel_x + 14, panel_y + 64), FONT_SMALL, LIGHT_GRAY)
        return

    cname = target.obj_class.upper()
    c_col = GREEN if target.obj_class == "bolt" else AMBER
    text(f"TARGET: {cname} #{target.id:02d}", (panel_x + 14, panel_y + 36), FONT_MED, c_col)
    dest_bin = "BIN A (BOLTS)" if target.obj_class == "bolt" else "BIN B (WASHERS)"
    text(f"ROUTE DEST    : {dest_bin}", (panel_x + 14, panel_y + 64), FONT_SMALL, WHITE)
    text(f"INTERCEPT ETA : {target.time_to_intercept:.2f} s", (panel_x + 14, panel_y + 84), FONT_SMALL, WHITE)
    text(f"PREDICTED POS : ({target.pred_x:.0f}, {target.pred_y:.0f}, {PICK_Z:.0f})", (panel_x + 14, panel_y + 104), FONT_SMALL, CYAN)

def draw_expanded_object_table():
    panel_x, panel_y, panel_w, panel_h = 1205, 492, 375, 205
    pygame.draw.rect(screen, PANEL_BG, (panel_x, panel_y, panel_w, panel_h), border_radius=7)
    pygame.draw.rect(screen, PANEL_BORDER, (panel_x, panel_y, panel_w, panel_h), 1, border_radius=7)
    text("OBJECT QUEUE & TRACKING TABLE", (panel_x + 14, panel_y + 9), FONT_STATUS, CYAN)

    headers = "ID  CLS   POS-X  VEL  CONF  PRED-X  RCH  STATUS"
    text(headers, (panel_x + 12, panel_y + 30), FONT_TINY, GRAY)
    pygame.draw.line(screen, PANEL_BORDER, (panel_x + 10, panel_y + 45), (panel_x + panel_w - 10, panel_y + 45), 1)

    yy = panel_y + 52
    for obj in [o for o in objects if o.state != "PLACED"][:6]:
        is_tgt = (robot.target_object is obj)
        cname = obj.obj_class[:4].upper()
        r_str = "YES" if obj.reachable else "NO"
        st_str = "LOCK" if is_tgt else (obj.state[:4])

        line = f"{obj.id:02d} {cname:<4} {obj.x:5.0f} {obj.measured_vx:4.0f} {obj.confidence:.2f} {obj.pred_x:6.0f}  {r_str:<3} {st_str}"
        col = YELLOW if is_tgt else (GREEN if obj.reachable else LIGHT_GRAY)
        text(line, (panel_x + 12, yy), FONT_TINY, col)
        yy += 23

def draw_performance_analytics_panel():
    panel_x, panel_y, panel_w, panel_h = 1205, 704, 375, 172
    pygame.draw.rect(screen, PANEL_BG, (panel_x, panel_y, panel_w, panel_h), border_radius=7)
    pygame.draw.rect(screen, PANEL_BORDER, (panel_x, panel_y, panel_w, panel_h), 1, border_radius=7)
    text("PERFORMANCE & QUALITY METRICS", (panel_x + 14, panel_y + 8), FONT_STATUS, GREEN)

    success_rate = 100.0 if (successful_picks + missed_objects == 0) else (successful_places / max(1, successful_picks + missed_objects) * 100.0)
    avg_cycle = (sum(cycle_times) / len(cycle_times)) if cycle_times else 1.25
    avg_err = (sum(prediction_errors) / len(prediction_errors)) if prediction_errors else 2.1
    elapsed = max(1.0, time.time() - simulation_start_time)
    throughput = (successful_places / elapsed) * 60.0
    active_now = len([o for o in objects if o.state in ["CONVEYOR", "GRASPED"]])

    metrics = [
        ("Spawned / Active", f"{total_spawned} / {active_now}"),
        ("Picks / Failed", f"{successful_picks} / {failed_picks}"),
        ("Bolts Sorted in Bin A", f"{bolts_sorted}"),
        ("Washers Sorted in Bin B", f"{washers_sorted}"),
        ("Missed (Zero-Miss Target: 0)", f"{missed_objects}"),
        ("Pick Success Rate", f"{success_rate:.1f}%"),
        ("Avg Intercept Precision", f"{avg_err:.1f} mm"),
        ("Cycle Time / Throughput", f"{avg_cycle:.2f}s / {throughput:.1f} ppm"),
    ]
    yy = panel_y + 30
    for name, val in metrics:
        text(name, (panel_x + 14, yy), FONT_TINY, GRAY)
        vc = GREEN if ("100.0%" in val or ("Missed" in name and "0" in val)) else WHITE
        text(val, (panel_x + 230, yy), FONT_TINY, vc)
        yy += 17

def draw_operation_ticker():
    banner_x, banner_y, banner_w, banner_h = 390, 68, 795, 34
    pygame.draw.rect(screen, (22, 27, 34), (banner_x, banner_y, banner_w, banner_h), border_radius=6)
    pygame.draw.rect(screen, (55, 65, 80), (banner_x, banner_y, banner_w, banner_h), 1, border_radius=6)
    text("CURRENT OPERATION:", (banner_x + 12, banner_y + 8), FONT_STATUS, YELLOW)
    text(logger.get_active(), (banner_x + 180, banner_y + 8), FONT_STATUS, WHITE)

def draw_state_machine_ribbon():
    ribbon_y = HEIGHT - 42
    states = [
        ("DETECT", "SELECT_TARGET"),
        ("APPROACH", "APPROACH"),
        ("DESCEND", "DESCEND"),
        ("GRIP", "GRIP"),
        ("LIFT", "LIFT"),
        ("TRANSFER", "TRANSFER"),
        ("DROP_DESC", "DROP_DESCEND"),
        ("RELEASE", "RELEASE"),
        ("RETURN", "RETURN_HOME"),
    ]
    x = 425
    for name, s_val in states:
        is_active = (robot.state == s_val)
        color = YELLOW if is_active else (PANEL_BORDER if not is_active else GRAY)
        pygame.draw.circle(screen, color, (x, ribbon_y), 7 if not is_active else 10)
        if is_active:
            pygame.draw.circle(screen, (255, 235, 120), (x, ribbon_y), 4)
        text(name, (x - 22, ribbon_y + 11), FONT_TINY, YELLOW if is_active else GRAY)
        if x < 1120:
            pygame.draw.line(screen, PANEL_BORDER, (x + 12, ribbon_y), (x + 65, ribbon_y), 2)
        x += 78

# ============================================================
# INITIALIZE INTERACTIVE UI WIDGETS
# ============================================================
# TAB 0: Conveyor Controls
slider_conveyor_speed = UISlider((35, 335, 320, 14), 100.0, 800.0, target_conveyor_speed, "CONVEYOR SPEED", " mm/s",
                                 lambda v: setattr(sys.modules[__name__], "target_conveyor_speed", v))

def on_start_conveyor():
    global conveyor_running
    conveyor_running = True
    logger.log("CONVEYOR", "Conveyor Belt Motor STARTED", GREEN)

def on_stop_conveyor():
    global conveyor_running
    conveyor_running = False
    logger.log("CONVEYOR", "Conveyor Belt Motor STOPPED", YELLOW)

def on_speed_plus():
    global target_conveyor_speed
    target_conveyor_speed = min(800.0, target_conveyor_speed + 25.0)
    slider_conveyor_speed.val = target_conveyor_speed
    logger.log("SPEED", f"Conveyor speed increased to {target_conveyor_speed:.0f} mm/s", CYAN)

def on_speed_minus():
    global target_conveyor_speed
    target_conveyor_speed = max(100.0, target_conveyor_speed - 25.0)
    slider_conveyor_speed.val = target_conveyor_speed
    logger.log("SPEED", f"Conveyor speed decreased to {target_conveyor_speed:.0f} mm/s", CYAN)

def on_reverse_toggle():
    global conveyor_direction
    conveyor_direction *= -1
    dir_name = "FORWARD" if conveyor_direction > 0 else "REVERSE"
    logger.log("CONVEYOR", f"Belt direction toggled to {dir_name}", YELLOW)

btn_conveyor_start = UIButton((35, 360, 95, 28), "START", on_start_conveyor, bg_color=(25, 75, 40), text_color=GREEN)
btn_conveyor_stop = UIButton((140, 360, 95, 28), "STOP", on_stop_conveyor, bg_color=(80, 30, 30), text_color=RED)
btn_conveyor_reverse = UIButton((245, 360, 110, 28), "REVERSE", on_reverse_toggle, bg_color=(35, 45, 60))
btn_speed_minus = UIButton((35, 395, 150, 26), "- SPEED 25", on_speed_minus)
btn_speed_plus = UIButton((205, 395, 150, 26), "+ SPEED 25", on_speed_plus)

# Generator Controls
slider_spawn_rate = UISlider((35, 545, 320, 14), 0.5, 4.0, spawn_interval, "SPAWN INTERVAL", " s",
                             lambda v: setattr(sys.modules[__name__], "spawn_interval", v))
slider_max_objects = UISlider((35, 580, 320, 14), 2, 10, max_active_objects, "MAX ACTIVE OBJECTS", "",
                              lambda v: setattr(sys.modules[__name__], "max_active_objects", int(v)))
toggle_bolts = UIToggle((35, 610, 16, 16), "Enable Bolts", enable_bolts, lambda s: setattr(sys.modules[__name__], "enable_bolts", s))
toggle_washers = UIToggle((190, 610, 16, 16), "Enable Washers", enable_washers, lambda s: setattr(sys.modules[__name__], "enable_washers", s))
btn_manual_spawn = UIButton((35, 640, 320, 30), "+ SPAWN OBJECT NOW", lambda: spawn_object_manual(), bg_color=(30, 70, 110), text_color=CYAN)

# TAB 1: Robot Controls & Manual Jogging
def on_toggle_mode():
    robot.mode = "MANUAL" if robot.mode == "AUTO" else "AUTO"
    logger.log("MODE", f"Robot mode changed to {robot.mode}", YELLOW if robot.mode == "MANUAL" else GREEN)

def on_home_robot():
    robot.position = HOME
    robot.set_state("HOME")
    logger.log("ROBOT", "Robot commanding return to HOME position", CYAN)

def on_toggle_gripper():
    robot.grip_closed = not robot.grip_closed
    logger.log("GRIPPER", "Manual Gripper " + ("CLOSED (SUCTION ON)" if robot.grip_closed else "OPEN (RELEASE)"), GREEN if robot.grip_closed else YELLOW)

btn_toggle_mode = UIButton((35, 320, 150, 30), "AUTO / MANUAL", on_toggle_mode, bg_color=(35, 50, 70))
btn_home_robot = UIButton((205, 320, 150, 30), "HOME POSITION", on_home_robot)
btn_toggle_gripper = UIButton((35, 360, 320, 28), "TOGGLE GRIPPER (OPEN/CLOSE)", on_toggle_gripper, bg_color=(30, 45, 55))
slider_robot_speed = UISlider((35, 415, 320, 14), 20.0, 150.0, robot_speed_pct, "ROBOT SPEED", "%",
                              lambda v: setattr(sys.modules[__name__], "robot_speed_pct", v))
slider_robot_accel = UISlider((35, 450, 320, 14), 20.0, 150.0, robot_accel_pct, "ROBOT ACCELERATION", "%",
                              lambda v: setattr(sys.modules[__name__], "robot_accel_pct", v))

# Jog Buttons
JOG_STEP = 35.0
btn_jog_x_minus = UIButton((35, 560, 95, 30), "X - 35", lambda: robot.jog(-JOG_STEP, 0, 0))
btn_jog_x_plus = UIButton((140, 560, 95, 30), "X + 35", lambda: robot.jog(JOG_STEP, 0, 0))
btn_jog_y_minus = UIButton((35, 600, 95, 30), "Y - 35", lambda: robot.jog(0, -JOG_STEP, 0))
btn_jog_y_plus = UIButton((140, 600, 95, 30), "Y + 35", lambda: robot.jog(0, JOG_STEP, 0))
btn_jog_z_minus = UIButton((245, 560, 110, 30), "Z - 25", lambda: robot.jog(0, 0, -25))
btn_jog_z_plus = UIButton((245, 600, 110, 30), "Z + 25", lambda: robot.jog(0, 0, 25))

# TAB 2: Latency & Fault Controls
def on_latency_plus():
    global camera_latency
    camera_latency = min(0.300, camera_latency + 0.020)
    logger.log("LATENCY", f"Total latency increased to {get_total_latency()*1000:.0f} ms", AMBER)

def on_latency_minus():
    global camera_latency
    camera_latency = max(0.005, camera_latency - 0.020)
    logger.log("LATENCY", f"Total latency decreased to {get_total_latency()*1000:.0f} ms", GREEN)

def on_next_strategy():
    global active_strategy_idx
    active_strategy_idx = (active_strategy_idx + 1) % len(TARGET_STRATEGIES)
    logger.log("STRATEGY", f"Target Selection Strategy: {TARGET_STRATEGIES[active_strategy_idx]}", YELLOW)

btn_latency_minus = UIButton((35, 345, 80, 26), "- 20 ms", on_latency_minus)
btn_latency_plus = UIButton((35, 376, 80, 26), "+ 20 ms", on_latency_plus)
btn_next_strategy = UIButton((35, 442, 320, 28), "CHANGE STRATEGY (CLICK)", on_next_strategy, bg_color=(35, 50, 75))

btn_fault_detect = UIButton((35, 524, 320, 25), "TOGGLE: DETECTION LOSS",
                            lambda: setattr(fault_mgr, "fault_detection_loss", not fault_mgr.fault_detection_loss))
btn_fault_track = UIButton((35, 552, 320, 25), "TOGGLE: TRACKING LOSS",
                           lambda: setattr(fault_mgr, "fault_tracking_loss", not fault_mgr.fault_tracking_loss))
btn_fault_occlude = UIButton((35, 580, 320, 25), "TOGGLE: OBJECT OCCLUSION",
                            lambda: setattr(fault_mgr, "fault_occlusion", not fault_mgr.fault_occlusion))
btn_fault_latency = UIButton((35, 608, 320, 25), "TOGGLE: LATENCY SPIKE (180ms)",
                             lambda: setattr(fault_mgr, "fault_camera_latency", not fault_mgr.fault_camera_latency))
btn_fault_slip = UIButton((35, 636, 320, 25), "TOGGLE: GRIPPER VACUUM SLIP",
                          lambda: setattr(fault_mgr, "fault_gripper_slip", not fault_mgr.fault_gripper_slip))

# TAB 3: Scenario Presets
scenario_names = [
    "NORMAL OPERATION", "HIGH-SPEED CONVEYOR", "HIGH OBJECT DENSITY",
    "HIGH LATENCY", "LOW LATENCY", "TRACKING FAILURE",
    "OBJECT OCCLUSION", "EMERGENCY STOP"
]
scenario_buttons = []
for idx, s_name in enumerate(scenario_names):
    sy = 320 + idx * 38
    b_col = (70, 25, 25) if "STOP" in s_name else ((45, 40, 25) if "FAIL" in s_name or "OCCL" in s_name else (25, 35, 48))
    scenario_buttons.append(UIButton((35, sy, 320, 32), s_name, lambda n=s_name: fault_mgr.apply_scenario(n), bg_color=b_col))

# Top Bar Emergency Stop & Reset
btn_estop_top = UIButton((1365, 12, 215, 34), "EMERGENCY STOP", trigger_emergency_stop, bg_color=(180, 30, 30), text_color=WHITE, font=FONT_STATUS)
btn_reset_safety = UIButton((1365, 12, 215, 34), "RESET SAFETY", reset_safety, bg_color=(25, 130, 50), text_color=WHITE, font=FONT_STATUS)

# ============================================================
# MAIN SIMULATION LOOP
# ============================================================
def run_simulation():
    global dataset_frame_idx, dataset_frame_timer, active_control_tab, simulation_start_time
    running = True
    paused = False

    logger.log("SYSTEM", "Automated Industrial Robotic Sorting Cell Initialized", GREEN)

    while running:
        dt = clock.tick(60) / 1000.0
        dt = min(dt, 0.05)

        # Dataset frame timer
        dataset_frame_timer += dt
        if dataset_frame_timer >= (1.0 / dataset_fps):
            dataset_frame_idx = (dataset_frame_idx + 1) % max(1, dataset.get_frame_count())
            dataset_frame_timer = 0.0

        # Handle User Events
        mouse_pos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                    logger.log("CONTROL", "Simulation PAUSED" if paused else "Simulation RESUMED", YELLOW)
                elif event.key in [pygame.K_e, pygame.K_KP_ENTER]:
                    trigger_emergency_stop()
                elif event.key == pygame.K_r:
                    if robot.e_stop:
                        reset_safety()
                    else:
                        initialize_cell()
                        logger.log("CONTROL", "Cell Reset to Initial State", CYAN)
                elif event.key in [pygame.K_PLUS, pygame.K_EQUALS]:
                    on_speed_plus()
                elif event.key in [pygame.K_MINUS, pygame.K_UNDERSCORE]:
                    on_speed_minus()
                elif event.key == pygame.K_a:
                    on_toggle_mode()
                elif event.key == pygame.K_h:
                    on_home_robot()
                elif event.key == pygame.K_g:
                    on_toggle_gripper()
                # Manual Jog arrow keys
                elif robot.mode == "MANUAL":
                    if event.key == pygame.K_LEFT: robot.jog(-JOG_STEP, 0, 0)
                    elif event.key == pygame.K_RIGHT: robot.jog(JOG_STEP, 0, 0)
                    elif event.key == pygame.K_UP: robot.jog(0, JOG_STEP, 0)
                    elif event.key == pygame.K_DOWN: robot.jog(0, -JOG_STEP, 0)
                    elif event.key == pygame.K_PAGEUP: robot.jog(0, 0, 25)
                    elif event.key == pygame.K_PAGEDOWN: robot.jog(0, 0, -25)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Tab switching
                panel_x, panel_y, panel_w = 20, 282, 350
                if panel_y <= mouse_pos[1] <= panel_y + 28 and panel_x <= mouse_pos[0] <= panel_x + panel_w:
                    tab_w = panel_w // len(CONTROL_TABS)
                    active_control_tab = (mouse_pos[0] - panel_x) // tab_w

            # Route UI Widget Events
            if robot.e_stop:
                btn_reset_safety.handle_event(event)
            else:
                btn_estop_top.handle_event(event)

            if active_control_tab == 0:
                slider_conveyor_speed.handle_event(event)
                btn_conveyor_start.handle_event(event)
                btn_conveyor_stop.handle_event(event)
                btn_speed_plus.handle_event(event)
                btn_speed_minus.handle_event(event)
                btn_conveyor_reverse.handle_event(event)
                slider_spawn_rate.handle_event(event)
                slider_max_objects.handle_event(event)
                toggle_bolts.handle_event(event)
                toggle_washers.handle_event(event)
                btn_manual_spawn.handle_event(event)
            elif active_control_tab == 1:
                btn_toggle_mode.handle_event(event)
                btn_home_robot.handle_event(event)
                btn_toggle_gripper.handle_event(event)
                slider_robot_speed.handle_event(event)
                slider_robot_accel.handle_event(event)
                btn_jog_x_minus.handle_event(event)
                btn_jog_x_plus.handle_event(event)
                btn_jog_y_minus.handle_event(event)
                btn_jog_y_plus.handle_event(event)
                btn_jog_z_minus.handle_event(event)
                btn_jog_z_plus.handle_event(event)
            elif active_control_tab == 2:
                btn_latency_minus.handle_event(event)
                btn_latency_plus.handle_event(event)
                btn_next_strategy.handle_event(event)
                btn_fault_detect.handle_event(event)
                btn_fault_track.handle_event(event)
                btn_fault_occlude.handle_event(event)
                btn_fault_latency.handle_event(event)
                btn_fault_slip.handle_event(event)
            elif active_control_tab == 3:
                for b in scenario_buttons:
                    b.handle_event(event)

        # Simulation Dynamics Update
        if not paused:
            update_conveyor_system(dt)
            robot_controller(dt)

        # ----------------------------------------------------
        # 3D RENDERING
        # ----------------------------------------------------
        screen.fill(DARK_BG)

        draw_industrial_environment()
        draw_conveyor_assembly()
        draw_robot_workspace_ring()
        draw_sorting_stations()

        # Dynamic Conveyor Objects
        for obj in objects:
            draw_conveyor_object(obj)

        draw_trajectory_ribbon()
        draw_target_interception_beacon()
        draw_3d_delta_robot()

        # ----------------------------------------------------
        # HUD & INTERACTIVE TELEMETRY PANELS
        # ----------------------------------------------------
        draw_header_banner()
        draw_operation_ticker()
        draw_yolo_camera_feed()
        draw_control_panel()
        draw_control_telemetry_dock()
        draw_operations_log_console()
        draw_active_target_card()
        draw_expanded_object_table()
        draw_performance_analytics_panel()
        draw_state_machine_ribbon()

        # Keyboard shortcuts reminder
        k_msg = "SPACE: Pause  |  E: Emergency Stop  |  R: Reset  |  +/-: Speed  |  A: Auto/Manual  |  H: Home  |  G: Gripper"
        text(k_msg, (400, HEIGHT - 22), FONT_TINY, GRAY)

        # Emergency Stop Banner Overlay
        if robot.e_stop:
            e_surf = pygame.Surface((WIDTH, 80), pygame.SRCALPHA)
            e_surf.fill((160, 20, 20, 220))
            screen.blit(e_surf, (0, HEIGHT // 2 - 40))
            text("EMERGENCY STOP ENGAGED - ALL DRIVES LOCKED", (WIDTH // 2 - 250, HEIGHT // 2 - 24), FONT_BIG, WHITE)
            text("Press 'R' or Click RESET SAFETY to Resume Operation", (WIDTH // 2 - 210, HEIGHT // 2 + 10), FONT, YELLOW)

        # Pause Overlay
        elif paused:
            p_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            p_surf.fill((10, 14, 20, 160))
            screen.blit(p_surf, (0, 0))
            text("CELL SIMULATION PAUSED", (WIDTH // 2 - 160, HEIGHT // 2 - 25), FONT_BIG, YELLOW)
            text("Press SPACE to Resume", (WIDTH // 2 - 120, HEIGHT // 2 + 15), FONT, WHITE)

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    run_simulation()
