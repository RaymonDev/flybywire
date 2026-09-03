import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'   # pygame headless, sin ventana
import pygame
import numpy as np
import csv
from game_engine import GameEngine
from mapping import game_state_to_stimulation, dn_response_to_force
from brain_game import BrainEngine

# === Configuración ===
FRAMES        = 600      # cuántos frames de juego generar
BRAIN_MS      = 20       # ms de cerebro simulados por frame de juego
OUT_DIR       = 'game_frames'
CSV_LOG       = 'game_log.csv'

os.makedirs(OUT_DIR, exist_ok=True)

# === Inicializa todo ===
print("Inicializando cerebro (tarda un poco la primera vez)...")
brain = BrainEngine()
game  = GameEngine()
pygame.init()
W, H = game.W, game.H
screen = pygame.Surface((W, H))   # superficie en memoria, no ventana
font = pygame.font.SysFont('monospace', 18)

# CSV de registro
log = open(CSV_LOG, 'w', newline='')
writer = csv.writer(log)
writer.writerow(['frame', 'fly_y', 'freq_dorsal', 'freq_ventral',
                 'DNp01', 'DNp02', 'DNp04', 'DNp11', 'force', 'alive', 'score'])

def draw(frame, rates, fd, fv, force):
    screen.fill((15, 20, 30))
    # tubos
    for p in game.pipes:
        top = p['gap_center'] - game.gap/2
        bot = p['gap_center'] + game.gap/2
        pygame.draw.rect(screen, (60, 180, 90), (p['x'], 0, 50, top))
        pygame.draw.rect(screen, (60, 180, 90), (p['x'], bot, 50, H - bot))
    # fly
    color = (240, 220, 60) if game.alive else (200, 60, 60)
    pygame.draw.circle(screen, color, (int(game.fly_x), int(game.fly_y)), 12)
    # panel de neuronas (barras)
    x0 = W - 180
    for i, dn in enumerate(['DNp01', 'DNp02', 'DNp04', 'DNp11']):
        val = rates.get(dn, 0)
        bar = int(val)
        y = 20 + i*28
        col = (100,150,255) if dn=='DNp11' else (150,150,150)
        pygame.draw.rect(screen, col, (x0, y, bar, 18))
        txt = font.render(f"{dn}:{val:.0f}", True, (230,230,230))
        screen.blit(txt, (x0, y-2))
    # info
    info = font.render(f"score:{game.score} D:{fd:.0f} V:{fv:.0f} F:{force:+.2f}",
                       True, (230,230,230))
    screen.blit(info, (10, 10))

# === Loop principal ===
print("Generando partida...")
for frame in range(FRAMES):
    if not game.alive:
        print(f"Fly murió en frame {frame}, score {game.score}")
        break

    # 1. estado del juego → estimulación
    fd, fv = game_state_to_stimulation(game)
    brain.set_stimulation(fd, fv)

    # 2. avanza el cerebro real BRAIN_MS
    rates = brain.step(BRAIN_MS)

    # 3. respuesta neuronal → fuerza → juego
    force = dn_response_to_force(rates)
    game.apply_control(force)
    game.update()

    # 4. registra
    writer.writerow([frame, f"{game.fly_y:.1f}", f"{fd:.1f}", f"{fv:.1f}",
                     f"{rates['DNp01']:.1f}", f"{rates['DNp02']:.1f}",
                     f"{rates['DNp04']:.1f}", f"{rates['DNp11']:.1f}",
                     f"{force:.3f}", game.alive, game.score])

    # 5. dibuja y guarda frame
    draw(frame, rates, fd, fv, force)
    pygame.image.save(screen, f"{OUT_DIR}/frame_{frame:04d}.png")

    if frame % 50 == 0:
        print(f"  frame {frame}: y={game.fly_y:.0f} DNp11={rates['DNp11']:.0f} "
              f"score={game.score}")

log.close()
print(f"\nListo. Frames en {OUT_DIR}/, log en {CSV_LOG}")
print(f"Para montar vídeo:")
print(f"  ffmpeg -framerate 30 -i {OUT_DIR}/frame_%04d.png -pix_fmt yuv420p game.mp4")