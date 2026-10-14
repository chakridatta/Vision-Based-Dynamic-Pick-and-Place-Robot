"""
render_preview_frame.py
Runs the simulation for 60 ticks in headless/dummy mode, renders all UI & 3D elements,
and saves a full-resolution 1600x900 screenshot to preview_render.png.
"""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame

pygame.init()
screen = pygame.display.set_mode((1600, 900))

import Dynamic_pick_and_place_yolo as sim
# Link simulation screen to this dummy screen
sim.screen = screen

# Step forward 75 ticks so an object is targeted, approach underway, and logs populated
dt = 1.0 / 60.0
for _ in range(75):
    sim.update_conveyor_system(dt)
    sim.robot_controller(dt)

# Render frame
screen.fill(sim.DARK_BG)
sim.draw_conveyor_belt()
sim.draw_robot_workspace_ring()
sim.draw_sorting_bins()

for obj in sim.objects:
    sim.draw_conveyor_object(obj)

sim.draw_trajectory_ribbon()
sim.draw_target_interception_beacon()
sim.draw_3d_delta_robot()

sim.draw_header_banner()
sim.draw_operation_ticker()
sim.draw_yolo_camera_feed()
sim.draw_detected_objects_table()
sim.draw_system_parameters_panel()
sim.draw_operations_log_console()
sim.draw_active_target_card()
sim.draw_performance_analytics_panel()
sim.draw_state_machine_ribbon()

pygame.image.save(screen, "preview_render.png")
print("Rendered and saved preview_render.png successfully!")
