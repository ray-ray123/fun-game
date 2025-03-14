from ursina.prefabs.first_person_controller import FirstPersonController
from ursina import *
from panda3d.core import ClockObject
from math import atan2, pi
import random
import time

app = Ursina()

toggle = False
last_shot_time = 0  # Track time of the last shot
cooldown_time = 0.09
ori_speed = 5
sprint_speed = 10

grass_texture = load_texture('assets/enemy.png')
stone_texture = load_texture('assets/stone_block.png')
brick_texture = load_texture('assets/brick_block.png')
dirt_texture = load_texture('assets/dirt_block.png')
sky_texture = load_texture('assets/skybox.png')
arm_texture = load_texture('assets/arm_texture.png')
player = FirstPersonController(position=Vec3(0, 1, 0))  # Spawn at the center

window.fps_counter.color = color.green
RENDER_DISTANCE = 15  # the number is how many blocks are visible

key_pressed_up = False
key_pressed_down = False
DEFAULT_FOV = 60
MAX_FOV = 120 

class Voxel(Button):
    def __init__(self, position=(0, 0, 0), texture=grass_texture):
        super().__init__(parent=scene,
                         position=position,
                         model='assets/block',
                         origin_y=0.5,
                         texture=texture,
                         color=color.white,
                         highlight_color=color.white,
                         scale=0.5)

    def update_visibility(self):
        """ Cull (hide) the voxel if it's too far from the player """
        if distance(self.position, player.position) > RENDER_DISTANCE:
            self.visible = False
        else:
            self.visible = True

class Sky(Entity):
    def __init__(self):
        super().__init__(parent=scene,
                         model='sphere',
                         texture=sky_texture,
                         scale=250,
                         double_sided=True)

class Weapon(Entity):
    def __init__(self, pos, rot, aimSpeed, scale, aimpos):
        self.original_position = pos
        self.aimpos = aimpos
        self.aimSpeed = aimSpeed

        super().__init__(
            parent=camera,  # Parent it to the camera to follow its movement
            model='assets/pistol1',
            texture=arm_texture,
            scale=scale,
            rotation=rot,  # Apply rotation in 3D space
            position=pos
        )
        self.sway_strength = 10
        self.sway_speed = 5.0
        self.sway_return_speed = 1.0

        # Store the initial mouse position for calculating movement delta
        self.last_mouse_position = Vec2(0, 0)
        self.last_shot_time = 0  # Time of last shot
        self.cooldown_time = cooldown_time  # Cooldown time between shots

    def input(self, key):
        if key == 'left mouse down' and self.last_shot_time == 0:
            self.start_fire()

    def start_fire(self):
        self.last_shot_time = time.time()  # Set last shot time to current time
        print("Fired")
        shoot()

        bullet_direction = camera.forward
        bullet_position = hand.world_position + Vec3(0, 0.1, 0)

        # Raycast and check if an enemy is hit
        ray_distance = 100
        hit_info = raycast(bullet_position, bullet_direction, ray_distance)
        if isinstance(hit_info.entity, Enemy):
            hit_info.entity.on_collision()

    def update(self):
        # Handle cooldown by checking the current time against the last shot time
        if self.last_shot_time > 0 and time.time() - self.last_shot_time >= self.cooldown_time:
            self.last_shot_time = 0

        # Aiming logic when the right mouse button is held
        if held_keys['right mouse']:
            target_position = Vec3(0, self.aimpos.y, self.aimpos.z)
            self.position = lerp(self.position, target_position, self.aimSpeed * time.dt)
            player.cursor.alpha = lerp(player.cursor.alpha, 0, 9 * time.dt)
            camera.fov = lerp(camera.fov, 65, 9 * time.dt)
        else:
            self.position = lerp(self.position, self.original_position, 9 * time.dt)
            player.cursor.alpha = lerp(player.cursor.alpha, 1, 9 * time.dt)
            camera.fov = lerp(camera.fov, 90, 9 * time.dt)

        if held_keys['right mouse']:
            self.rotation = lerp(self.rotation, camera.rotation, self.aimSpeed * time.dt)

hand = Weapon(Vec3(0.1, -0.2, 0.65), Vec3(0, 0, 0), 9, 0.12, Vec3(0, -0.16, 0.75))
print(f"Children of {hand.name}: {hand.children}")

class Enemy(Entity):
    def __init__(self, position):
        random_color = color.rgb(random.randint(0, 255) / 255, 
                                 random.randint(0, 255) / 255, 
                                 random.randint(0, 255) / 255)
        super().__init__(parent=scene,
                         model='cube',
                         color=color.red,
                         texture=grass_texture,
                         position=position,
                         scale=(1, 2, 1))
        self.collider = BoxCollider(entity=self, center=Vec3(0, 0, 0))
        self.speed = 1.65  # Movement speed towards the player
        self.falling = False

    def avoid_overlap(self):
        for entity in scene.entities:
            if isinstance(entity, Enemy) and entity != self:
                if self.intersects(entity):
                    self.position.x += random.uniform(-1, 1)
                    self.position.z += random.uniform(-1, 1)

    def update(self):
        if not self.falling:
            self.avoid_overlap()
            direction = Vec3(player.position.x - self.position.x, 0, player.position.z - self.position.z)
            distance_to_player = direction.length()

            if distance_to_player > 0:
                target_rotation = Vec3(0, atan2(direction.x, direction.z) * (180 / pi), 0)
                self.rotation_y = lerp(self.rotation_y, target_rotation.y, 5 * time.dt)
                direction = direction.normalized()
                self.position += direction * self.speed * time.dt

    def on_collision(self):
        if not self.falling:
            self.falling = True
            self.animate_rotation(Vec3(self.rotation.x, self.rotation.y, 90), duration=0.23, curve=curve.linear)
            self.animate_position(Vec3(self.position.x,.25,self.position.z), duration=0.23, curve=curve.linear)


            invoke(self.flash_effect, delay=0.23)  # Start flashing after falling

    def flash_effect(self):
        flash_sequence = Sequence(
            Func(self.set_color, color.white),
            Wait(0.1),
            Func(self.set_color, color.red),
            Wait(0.1),
            Func(self.set_color, color.white),
            Wait(0.1),
            Func(destroy, self)
        )
        flash_sequence.start()

    def set_color(self, new_color):
        self.color = new_color

class Bullet(Entity):
    def __init__(self, position, direction):
        super().__init__(parent=scene,
                         model='sphere',
                         color=color.red,
                         scale=0.05,
                         position=position)
        self.direction = direction
        self.speed = 200
        self.lifetime = 5
        self.timer = 0
        self.gravity = 9.8
        self.collider = SphereCollider(entity=self, center=Vec3(0, 0, 0))

    def update(self):
        self.timer += time.dt
        self.position += self.direction * self.speed * time.dt
        self.position.y -= self.gravity * time.dt

        for enemy in scene.entities:
            if isinstance(enemy, Enemy) and self.intersects(enemy):
                enemy.on_collision()
                return

        if self.timer > self.lifetime:
            destroy(self)


sky = Sky()
num_enemies = 15  # Number of enemies to spawn per round
spawn_area = (25, 25)

def spawn_enemies(num_enemies, spawn_area=(25, 25)):
    min_spawn_distance = 25  # Do not spawn an enemy if closer than this distance to the player.
    spawned = 0
    while spawned < num_enemies:
        x = random.randint(-spawn_area[0], spawn_area[0])
        z = random.randint(-spawn_area[1], spawn_area[1])
        spawn_pos = Vec3(x, 1, z)
        if distance(spawn_pos, player.position) < min_spawn_distance:
            continue  # Skip if too near the player.
        enemy = Enemy(position=(x, 1, z))
        enemy.avoid_overlap()
        spawned += 1

# Timer text for countdown between rounds.
timer_text = Text(text='', position=(0, 0.4), origin=(0, 0), scale=2, color=color.white)
timer_text.enabled = False
round_timer = None  # Global variable to track the countdown

# Initial enemy spawn if desired.


pl = Entity(model='plane', scale=55, position=Vec3(0, 0, 0), collider='mesh', texture='white_cube')

def update():
    global toggle, round_timer

    # Adjust player speed.
    if held_keys['left shift']:
        player.speed = sprint_speed
    else:
        player.speed = ori_speed

    # Adjust Field of View (FOV) with arrow keys.
    global key_pressed_up, key_pressed_down
    if held_keys['up arrow'] and not key_pressed_up:
        camera.fov += 10
        camera.fov = min(camera.fov, MAX_FOV)
        key_pressed_up = True
    elif held_keys['down arrow'] and not key_pressed_down:
        camera.fov -= 10
        camera.fov = max(camera.fov, DEFAULT_FOV)
        key_pressed_down = True

    if not held_keys['up arrow']:
        key_pressed_up = False
    if not held_keys['down arrow']:
        key_pressed_down = False

    # Change FPS counter color based on performance.
    fps = int(window.fps_counter.text)
    if fps > 120:
        window.fps_counter.color = color.green
    elif 60 <= fps <= 69:
        window.fps_counter.color = color.yellow
    elif fps < 30:
        window.fps_counter.color = color.red

    # Update voxel visibility.
    for voxel in voxels.values():
        voxel.update_visibility()

    # Check enemy count and handle round timer.
    enemy_count = sum(1 for entity in scene.entities if isinstance(entity, Enemy))
    if enemy_count <= 0:
        # Start the round timer if it hasn't started yet.
        if round_timer is None:
            round_timer = 6.5
            timer_text.enabled = True
        else:
            round_timer -= time.dt
            timer_text.text = f'Next round in: {round_timer:.1f}s'
            if round_timer <= 0:
                timer_text.enabled = False
                spawn_enemies(num_enemies, spawn_area)
                round_timer = None

def shoot():
    hand.animate_rotation(Vec3(-3.5, 0, 0), 0.01)
    invoke(idle, delay=0.075)

def idle():
    hand.animate_rotation(Vec3(0, 0, 0), 0.15)

# Create voxels (the environment).
voxels = {}
def Run_voxels():
    for z in range(15):
        for x in range(15):
            for y in range(1):
                if y == 0:
                    voxel = Voxel(position=(x, -y, z), texture=grass_texture)
                elif y in [1]:
                    voxel = Voxel(position=(x, -y, z), texture=dirt_texture)
                elif y >= 2:
                    voxel = Voxel(position=(x, -y, z), texture=stone_texture)
                    voxels[(x, -y, z)] = voxel

app.run()
