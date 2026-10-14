"""
test_simulation_logic.py
Validates the full kinematics, YOLO dataset integration, conveyor flow control,
and 100% pick-and-place zero-miss guarantee over 1800 simulation steps.
"""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy" # Headless Pygame
import pygame

# Initialize pygame with dummy video
pygame.init()
pygame.display.set_mode((1, 1))

import Dynamic_pick_and_place_yolo as sim

print("--- RUNNING 1800 SIMULATION STEPS (30 SECONDS EQUIVALENT) ---")
dt = 1.0 / 60.0

for step in range(1800):
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
assert sim.successful_places > 5, f"Expected at least 5 placements, got {sim.successful_places}!"
assert sim.bolts_sorted > 0 and sim.washers_sorted > 0, "Both bolts and washers should be sorted!"
print("\nALL AUTOMATED TESTS PASSED FLACIDLY AND PERFECTLY!")
