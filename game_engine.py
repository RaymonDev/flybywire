import numpy as np

class GameEngine:
    """
    Flappy Bird minimalista. El fly tiene una posición vertical y
    una velocidad. Los tubos se acercan desde la derecha con un hueco.
    El control vertical vendrá del cerebro (se aplica desde fuera).
    """
    def __init__(self, height=600, width=800, gap=140, pipe_speed=4.0):
        self.H = height
        self.W = width
        self.gap = gap
        self.pipe_speed = pipe_speed

        self.fly_x = 150
        self.fly_y = height / 2
        self.fly_vy = 0.0

        self.gravity = 0
        self.pipes = []
        self.spawn_timer = 0
        self.spawn_interval = 90   # frames entre tubos
        self.score = 0
        self.alive = True
        self._spawn_pipe()

    def _spawn_pipe(self):
        # alterna huecos altos y bajos para forzar movimiento
        if not hasattr(self, '_last_high'):
            self._last_high = False
        if self._last_high:
            gap_center = np.random.uniform(self.H*0.55, self.H*0.8)   # bajo
        else:
            gap_center = np.random.uniform(self.H*0.2, self.H*0.45)   # alto
        self._last_high = not self._last_high
        self.pipes.append({'x': self.W, 'gap_center': gap_center, 'scored': False})

    def apply_control(self, vertical_force):
        # mezcla suave: la nueva velocidad es parte de la vieja + parte del control
        self.fly_vy = 0.6 * self.fly_vy + 0.4 * (vertical_force * 20)

    def update(self):
        if not self.alive:
            return
        # física del fly
        self.fly_vy += self.gravity
        self.fly_vy *= 0.9   # amortiguación
        self.fly_y += self.fly_vy
        # límites
        if self.fly_y < 0 or self.fly_y > self.H:
            self.alive = False

        # mover tubos
        for p in self.pipes:
            p['x'] -= self.pipe_speed
        self.pipes = [p for p in self.pipes if p['x'] > -60]

        # spawn
        self.spawn_timer += 1
        if self.spawn_timer >= self.spawn_interval:
            self._spawn_pipe()
            self.spawn_timer = 0

                # colisiones y score (con hitbox real)
        fly_r = 12   # radio del fly
        for p in self.pipes:
            # ¿el fly solapa horizontalmente con el tubo?
            pipe_left  = p['x']
            pipe_right = p['x'] + 50
            if pipe_right > self.fly_x - fly_r and pipe_left < self.fly_x + fly_r:
                top = p['gap_center'] - self.gap/2
                bot = p['gap_center'] + self.gap/2
                # colisión si el fly (con su radio) toca arriba o abajo
                if self.fly_y - fly_r < top or self.fly_y + fly_r > bot:
                    self.alive = False
            # score solo si pasó limpiamente el centro del tubo
            if not p['scored'] and p['x'] + 50 < self.fly_x - fly_r:
                p['scored'] = True
                self.score += 1

    def nearest_pipe(self):
        """El tubo objetivo: el primero que el fly aún no ha pasado del todo."""
        fly_r = 12
        # tubos cuyo borde derecho aún no ha quedado atrás del fly
        ahead = [p for p in self.pipes if p['x'] + 50 > self.fly_x - fly_r]
        return min(ahead, key=lambda p: p['x']) if ahead else None