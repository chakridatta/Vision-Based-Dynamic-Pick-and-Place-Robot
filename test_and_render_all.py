"""
test_and_render_all.py
Runs headless simulation steps on Dynamic_pick_and_place_8, verifies kinematics,
state machine, pick-and-place sorting, and saves preview screenshots across all tabs.
"""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame

pygame.init()
screen = pygame.display.set_mode((1600, 900))

import Dynamic_pick_and_place_8 as sim
sim.screen = screen

print("--- RUNNING 1200 SIMULATION STEPS (20 SECONDS EQUIVALENT) ---")
dt = 1.0 / 60.0

for step in range(1200):
    sim.update_conveyor_system(dt)
    sim.robot_controller(dt)
    
    if (step + 1) % 300 == 0:
        print(f"Step {step+1:04d} | State: {sim.robot.state:<12} | "
              f"Picks: {sim.successful_picks} | Places: {sim.successful_places} "
              f"(Bolts: {sim.bolts_sorted}, Washers: {sim.washers_sorted}) | "
              f"Missed: {sim.missed_objects} | Conveyor: {sim.current_conveyor_speed:.0f} mm/s")

print("\n--- FINAL SIMULATION TEST RESULTS ---")
print(f"Total Detected / Spawned : {sim.total_detected}")
print(f"Successful Picks         : {sim.successful_picks}")
print(f"Successful Placements    : {sim.successful_places}")
print(f"  - Bolts in Bin A       : {sim.bolts_sorted}")
print(f"  - Washers in Bin B     : {sim.washers_sorted}")
print(f"Missed Objects           : {sim.missed_objects} (Target: 0)")
pick_rate = (sim.successful_places / max(1, sim.successful_picks + sim.missed_objects)) * 100.0
print(f"Pick & Place Success Rate: {pick_rate:.1f}%")

assert sim.missed_objects == 0, f"Expected 0 missed objects, but got {sim.missed_objects}!"
assert sim.successful_places >= 3, f"Expected at least 3 placements, got {sim.successful_places}!"
assert sim.bolts_sorted > 0 and sim.washers_sorted > 0, "Both bolts and washers should be sorted!"
print("Logic verification passed successfully!")

# Render Tab 0 (Conveyor & Generator)
sim.active_control_tab = 0
sim.screen.fill(sim.DARK_BG)
sim.draw_industrial_environment()
sim.draw_conveyor_assembly()
sim.draw_robot_workspace_ring()
sim.draw_sorting_stations()
for obj in sim.objects:
    sim.draw_conveyor_object(obj)
sim.draw_trajectory_ribbon()
sim.draw_target_interception_beacon()
sim.draw_3d_delta_robot()
sim.draw_header_banner()
sim.draw_operation_ticker()
sim.draw_yolo_camera_feed()
sim.draw_control_panel()
sim.draw_control_telemetry_dock()
sim.draw_operations_log_console()
sim.draw_active_target_card()
sim.draw_expanded_object_table()
sim.draw_performance_analytics_panel()
sim.draw_state_machine_ribbon()
pygame.image.save(screen, "preview_render_tab0.png")
print("Saved preview_render_tab0.png")

# Render Tab 1 (Robot Control & Manual Jog)
sim.active_control_tab = 1
sim.screen.fill(sim.DARK_BG)
sim.draw_industrial_environment()
sim.draw_conveyor_assembly()
sim.draw_robot_workspace_ring()
sim.draw_sorting_stations()
for obj in sim.objects:
    sim.draw_conveyor_object(obj)
sim.draw_trajectory_ribbon()
sim.draw_target_interception_beacon()
sim.draw_3d_delta_robot()
sim.draw_header_banner()
sim.draw_operation_ticker()
sim.draw_yolo_camera_feed()
sim.draw_control_panel()
sim.draw_control_telemetry_dock()
sim.draw_operations_log_console()
sim.draw_active_target_card()
sim.draw_expanded_object_table()
sim.draw_performance_analytics_panel()
sim.draw_state_machine_ribbon()
pygame.image.save(screen, "preview_render_tab1.png")
print("Saved preview_render_tab1.png")

# Render Tab 2 (Latency & Fault Injection)
sim.active_control_tab = 2
sim.screen.fill(sim.DARK_BG)
sim.draw_industrial_environment()
sim.draw_conveyor_assembly()
sim.draw_robot_workspace_ring()
sim.draw_sorting_stations()
for obj in sim.objects:
    sim.draw_conveyor_object(obj)
sim.draw_trajectory_ribbon()
sim.draw_target_interception_beacon()
sim.draw_3d_delta_robot()
sim.draw_header_banner()
sim.draw_operation_ticker()
sim.draw_yolo_camera_feed()
sim.draw_control_panel()
sim.draw_control_telemetry_dock()
sim.draw_operations_log_console()
sim.draw_active_target_card()
sim.draw_expanded_object_table()
sim.draw_performance_analytics_panel()
sim.draw_state_machine_ribbon()
pygame.image.save(screen, "preview_render_tab2.png")
print("Saved preview_render_tab2.png")

# Render Tab 3 (Scenario Presets)
sim.active_control_tab = 3
sim.screen.fill(sim.DARK_BG)
sim.draw_industrial_environment()
sim.draw_conveyor_assembly()
sim.draw_robot_workspace_ring()
sim.draw_sorting_stations()
for obj in sim.objects:
    sim.draw_conveyor_object(obj)
sim.draw_trajectory_ribbon()
sim.draw_target_interception_beacon()
sim.draw_3d_delta_robot()
sim.draw_header_banner()
sim.draw_operation_ticker()
sim.draw_yolo_camera_feed()
sim.draw_control_panel()
sim.draw_control_telemetry_dock()
sim.draw_operations_log_console()
sim.draw_active_target_card()
sim.draw_expanded_object_table()
sim.draw_performance_analytics_panel()
sim.draw_state_machine_ribbon()
pygame.image.save(screen, "preview_render_tab3.png")
print("Saved preview_render_tab3.png")

print("ALL PREVIEWS SAVED SUCCESSFULLY!")
