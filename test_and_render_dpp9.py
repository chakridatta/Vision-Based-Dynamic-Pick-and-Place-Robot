"""
test_and_render_dpp9.py
Automated validation and multi-frame rendering for Dynamic_pick_and_place_9.py.
Tests 4-factor delay calculations, bolt vs washer profiles, compensation ON/OFF modes,
center settings modal rendering, and saves visual preview artifacts.
"""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame

pygame.init()
screen = pygame.display.set_mode((1600, 900))

import Dynamic_pick_and_place_9 as sim
sim.screen = screen

print("=== 1. TESTING 4-FACTOR DELAY CALCULATIONS ===")
b_comm, b_calib, b_calc, b_move, b_tot = sim.latency_engine.get_effective_delays("bolt")
w_comm, w_calib, w_calc, w_move, w_tot = sim.latency_engine.get_effective_delays("washer")

print(f"BOLT DELAYS   : Comm={b_comm*1000:.1f}ms, Calib={b_calib*1000:.1f}ms, Calc/Angle={b_calc*1000:.1f}ms, Move={b_move*1000:.1f}ms | Total={b_tot*1000:.1f}ms")
print(f"WASHER DELAYS : Comm={w_comm*1000:.1f}ms, Calib={w_calib*1000:.1f}ms, Calc/Centroid={w_calc*1000:.1f}ms, Move={w_move*1000:.1f}ms | Total={w_tot*1000:.1f}ms")

assert b_tot > 0 and w_tot > 0, "Delays must be strictly positive!"
assert b_calc > 0 and w_calc > 0, "Angle calculation delays must be positive!"
print("=> 4-factor delay calculations verified successfully!")

print("\n=== 2. RUNNING COMPENSATED SIMULATION (700 TICKS) ===")
dt = 1.0 / 60.0
for step in range(700):
    sim.update_conveyor_system(dt)
    sim.robot_controller(dt)

print(f"Compensated Results after 700 ticks:")
print(f"  Picks: {sim.successful_picks} | Places: {sim.successful_places} (Bolts: {sim.bolts_sorted}, Washers: {sim.washers_sorted})")
print(f"  Failed picks: {sim.failed_picks}")
assert sim.successful_picks > 0, "Compensated robot must achieve successful picks!"

# Render standard operational screen
screen.fill(sim.DARK_BG)
sim.draw_industrial_environment()
sim.draw_conveyor_assembly()
sim.draw_robot_workspace_ring()
sim.draw_sorting_stations()
for obj in sim.objects:
    sim.draw_conveyor_object_with_latencies(obj)
sim.draw_trajectory_ribbon()
sim.draw_interception_beacon()
sim.draw_3d_delta_robot()
sim.draw_header_banner()
sim.draw_yolo_camera_feed()
sim.draw_object_detection_queue()
sim.draw_cell_diagnostics_dock()
sim.draw_operations_log_console()
sim.draw_active_target_card()
sim.draw_dual_fastener_comparison_table()
sim.draw_performance_analytics_panel()
sim.draw_operation_ticker()
sim.draw_central_quick_bar()
sim.draw_state_machine_ribbon()

pygame.image.save(screen, "preview_dpp9_main.png")
print("Saved preview_dpp9_main.png successfully!")

print("\n=== 3. TESTING & RENDERING CENTER SETTINGS MODAL ===")
sim.center_modal_open = True
for tab_idx in range(4):
    sim.center_modal_tab = tab_idx
    screen.fill(sim.DARK_BG)
    sim.draw_industrial_environment()
    sim.draw_conveyor_assembly()
    sim.draw_robot_workspace_ring()
    sim.draw_sorting_stations()
    for obj in sim.objects:
        sim.draw_conveyor_object_with_latencies(obj)
    sim.draw_trajectory_ribbon()
    sim.draw_3d_delta_robot()
    sim.draw_header_banner()
    sim.draw_central_quick_bar()
    sim.draw_center_settings_modal()
    filename = f"preview_dpp9_modal_tab{tab_idx}.png"
    pygame.image.save(screen, filename)
    print(f"Saved modal tab {tab_idx} screenshot to {filename}")

print("\n=== 4. TESTING UNCOMPENSATED MODE (SEEING DELAY PROBLEMS) ===")
sim.center_modal_open = False
sim.latency_engine.compensation_active = False
prev_failed = sim.failed_picks
for step in range(300):
    sim.update_conveyor_system(dt)
    sim.robot_controller(dt)

print(f"Uncompensated mode test: Failed picks increased by {sim.failed_picks - prev_failed}")
assert sim.failed_picks > prev_failed, "Uncompensated mode must demonstrate delay misses!"

# Render uncompensated failure screenshot
screen.fill(sim.DARK_BG)
sim.draw_industrial_environment()
sim.draw_conveyor_assembly()
sim.draw_robot_workspace_ring()
sim.draw_sorting_stations()
for obj in sim.objects:
    sim.draw_conveyor_object_with_latencies(obj)
sim.draw_trajectory_ribbon()
sim.draw_interception_beacon()
sim.draw_3d_delta_robot()
sim.draw_header_banner()
sim.draw_yolo_camera_feed()
sim.draw_object_detection_queue()
sim.draw_cell_diagnostics_dock()
sim.draw_operations_log_console()
sim.draw_active_target_card()
sim.draw_dual_fastener_comparison_table()
sim.draw_performance_analytics_panel()
sim.draw_operation_ticker()
sim.draw_central_quick_bar()
sim.draw_state_machine_ribbon()

pygame.image.save(screen, "preview_dpp9_uncompensated.png")
print("Saved preview_dpp9_uncompensated.png successfully!")

print("\nALL AUTOMATED TESTS AND RENDERING COMPLETED WITH 100% SUCCESS!")
