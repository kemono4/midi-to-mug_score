MIDIFILE = "YOUR MIDI FILE"

import pygame
import sys
import time
import math
import json
import os
import music21
from music21.tempo import MetronomeMark

pygame.init()
pygame.font.init()
pygame.mixer.init()

SCREEN_WIDTH = 500
SCREEN_HEIGHT = 600
SCREEN_TITLE = "Rhythm Game"
PREP_TIME = 2.0
SPEED = 800

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
DARK_GRAY = (10, 10, 10)
GRAY = (50, 50, 50)
RED = (255, 0, 0)
LIGHT_BLUE = (100, 180, 255)
BLUE = (0, 100, 255)
DARK_BLUE = (0, 40, 120)

NOTE_COLORS = [WHITE, LIGHT_BLUE, WHITE, LIGHT_BLUE, WHITE, LIGHT_BLUE, WHITE]
step_to_number = {'C': 0, 'D': 1, 'E': 2, 'F': 3, 'G': 4, 'A': 5, 'B': 6}

KEYS = {
    pygame.K_a: 0,
    pygame.K_s: 1,
    pygame.K_d: 2,
    pygame.K_SPACE: 3,
    pygame.K_j: 4,
    pygame.K_k: 5,
    pygame.K_l: 6
}

SCALE_TO_KEY = {
    0: "A",
    1: "S",
    2: "D",
    3: "SP",
    4: "J",
    5: "K",
    6: "L"
}

# judgement window（s）
PERFECT_WINDOW = 0.05
GOOD_WINDOW = 0.1
OK_WINDOW = 0.15

# score
MAX_SCORE = 200000
GOOD_WEIGHT = 0.5
OK_WEIGHT = 0.1

def offset_to_seconds(n, tempo_changes):
    seconds = 0
    prev_offset = 0

    for (start_offset, end_offset, mark) in tempo_changes:
        bpm = mark.number
        beat_duration = 60 / bpm
        if n.offset < end_offset:
            seconds += (n.offset - prev_offset) * beat_duration
            break
        else:
            seconds += (end_offset - start_offset) * beat_duration
            prev_offset = end_offset

    return seconds

class Note:
    def __init__(self, time, track, midi_note=None):
        self.time = time # hit timing
        self.track = track  # track 0 - 6
        self.midi_note = midi_note  # note information
        self.y = -20
        self.width = SCREEN_WIDTH / 7 - 10
        self.height = 15
        self.hit = False
        self.judgement = None
        self.color = NOTE_COLORS[track]

    def get_x(self):
        track_width = SCREEN_WIDTH / 7
        return self.track * track_width + (track_width - self.width) / 2

    def update(self, elapsed_time, speed, judgement_line_y):
        if not self.hit:
            top_to_judgement = judgement_line_y
            falling_time = top_to_judgement / speed
            appear_time = self.time - falling_time
            time_falling = elapsed_time - appear_time

            if elapsed_time < appear_time:
                self.y = -20
            else:
                self.y = time_falling * speed

    def draw(self, screen):
        if not self.hit and self.y > -self.height and self.y < SCREEN_HEIGHT + self.height:
            pygame.draw.rect(
                screen,
                self.color,
                (self.get_x(), self.y - self.height / 2, self.width, self.height)
            )

class RhythmGame:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(SCREEN_TITLE)
        self.clock = pygame.time.Clock()
        
        self.font_large = pygame.font.SysFont("Arial", 24)
        self.font_medium = pygame.font.SysFont("Arial", 18)
        self.font_small = pygame.font.SysFont("Arial", 14)
        
        self.notes = []
        self.start_time = None
        self.elapsed_time = 0
        self.song_end_time = 0
        self.is_playing = False
        self.score = 0
        self.max_score = 0
        self.combo = 0
        self.max_combo = 0
        self.judgements = {"PERFECT": 0, "GOOD": 0, "OK": 0, "MISS": 0}
        self.current_judgement = None
        self.judgement_time = 0
        self.pressed_keys = set()
        self.key_pressed_time = {}
        self.total_notes = 0
        
        self.bpm = 120
        self.note_speed = SPEED
        self.fps = 60
        
        self.judgement_line_y = SCREEN_HEIGHT - 80

    def load_midi(self, midi_file, bpm = None):
        self.notes = []
        
        try:
            midi = music21.converter.parse(midi_file)
            pygame.mixer.music.load(midi_file)
            
            # get key signature
            key = None
            for elem in midi.flatten():
                if isinstance(elem, music21.key.Key):
                    key = elem
                    break
            
            if key:
                print(f"Key: {key}")
            
            # get BPM
            if bpm is None:
                for tempo in midi.flatten().getElementsByClass(music21.tempo.MetronomeMark):
                    self.bpm = tempo.number
                    break
            else:
                self.bpm = bpm

            # sof-lan point
            tempo_changes = midi.flatten().metronomeMarkBoundaries()
            bpm_values = [mark.number for _, _, mark in tempo_changes if isinstance(mark, MetronomeMark)]
            if (len(tempo_changes) > 1):
                print(f"BPM: {min(bpm_values)} - {max(bpm_values)}")
            else:
                print(f"BPM: {self.bpm}")

            last_time = 0.0
            
            notes_data = []
            for note in midi.flatten().notes:
                # get pitch
                scale_degree = 0

                time_seconds = offset_to_seconds(note, tempo_changes) + PREP_TIME
                if time_seconds > last_time:
                    last_time = time_seconds
                
                if isinstance(note, music21.note.Note):
                    # single note
                    if key:
                        note.pitch.midi -= key.tonic.pitchClass - 12
                    scale_degree = step_to_number[note.pitch.step]
                    new_note = {
                        "time": time_seconds,
                        "track": scale_degree
                    }
                    if not any(float(exist["time"]) == time_seconds and exist["track"] == scale_degree for exist in notes_data):
                            notes_data.append(new_note)
                elif isinstance(note, music21.chord.Chord):
                    # chord
                    for n in note.pitches:
                        if key:
                            n.midi -= key.tonic.pitchClass - 12
                        if key.mode == "minor":
                            n.midi += 2
                        scale_degree = step_to_number[n.step]
                        new_note = {
                            "time": time_seconds,
                            "track": scale_degree
                        }
                        if not any(float(exist["time"]) == time_seconds and exist["track"] == scale_degree for exist in notes_data):
                            notes_data.append(new_note)
                else:
                    continue
                

            
            for note_data in notes_data:
                self.notes.append(Note(
                    time=note_data["time"],
                    track=note_data["track"],
                ))

            self.song_end_time = last_time + 3.0 
            self.total_notes = len(self.notes)
            self.max_score = MAX_SCORE
            
            print(f"Successfully loaded {self.total_notes} notes")
            
            # save to json (parsed score, best local score...)
            self.save_notes_to_json(notes_data, f"{os.path.splitext(midi_file)[0]}_notes.json")
            
        except Exception as e:
            print(f"Failed to load MIDI: {e}")
            raise e

    def save_notes_to_json(self, notes_data, output_file):
        with open(output_file, "w") as f:
            json.dump(notes_data, f, indent=2)
        print(f"data has been saved to {output_file}")

    def draw_tracks(self):
        track_width = SCREEN_WIDTH / 7
        
        self.screen.fill(BLACK)

        # color gradient
        background = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        for y in range(SCREEN_HEIGHT):
            darkness = max(0, min(255, int(10 + (y / SCREEN_HEIGHT) * 40)))
            background.fill((0, 0, darkness), (0, y, SCREEN_WIDTH, 1))
        self.screen.blit(background, (0, 0))
        
        for i in range(7):
            x = i * track_width
            
            pygame.draw.rect(
                self.screen,
                DARK_GRAY if (i % 2) else BLACK,
                (x, 0, track_width, SCREEN_HEIGHT)
            )
            
            # press effect
            if i in [KEYS[key] for key in self.pressed_keys if key in KEYS]:
                pygame.draw.rect(
                    self.screen,
                    DARK_BLUE,
                    (x + 5, self.judgement_line_y - 5, track_width - 10, 30)
                )
                
                glow_surf = pygame.Surface((track_width, 40), pygame.SRCALPHA)
                pygame.draw.rect(
                    glow_surf,
                    (100, 150, 255, 100),
                    (0, 0, track_width, 40),
                    border_radius=5
                )
                self.screen.blit(glow_surf, (x, self.judgement_line_y - 10))

    def draw_judgement_line(self):
        pygame.draw.line(
            self.screen,
            RED,
            (0, self.judgement_line_y),
            (SCREEN_WIDTH, self.judgement_line_y),
            3
        )
        
        # effect
        for i in range(3):
            alpha = 100 - i * 30
            pygame.draw.line(
                self.screen,
                (*RED[:3], alpha),
                (0, self.judgement_line_y + i + 1),
                (SCREEN_WIDTH, self.judgement_line_y + i + 1),
                1
            )
        
        track_width = SCREEN_WIDTH / 7
        
        for i in range(7):
            x = i * track_width
            
            # background
            pygame.draw.rect(
                self.screen,
                BLUE if (i % 2) else GRAY,
                (x + 5, self.judgement_line_y + 5, track_width - 10, 25)
            )
            
            # text
            key_text = self.font_small.render(SCALE_TO_KEY[i], True, WHITE)
            text_rect = key_text.get_rect(center=(x + track_width/2, self.judgement_line_y + 17))
            self.screen.blit(key_text, text_rect)

    def draw_info(self):
        score_text = self.font_large.render(f"Score: {self.score}", True, WHITE)
        self.screen.blit(score_text, (10, 10))
        
        if self.max_score > 0:
            percentage = (self.score / self.max_score) * 100
        else:
            percentage = 0
        percentage_text = self.font_medium.render(f"{percentage:.2f}%", True, WHITE)
        self.screen.blit(percentage_text, (10, 40))
        
        if self.combo > 1:
            combo_text = self.font_large.render(f"Combo: {self.combo}", True, LIGHT_BLUE)
            combo_rect = combo_text.get_rect(center=(SCREEN_WIDTH / 2, 30))
            self.screen.blit(combo_text, combo_rect)
        
        notes_text = self.font_medium.render(f"Note: {self.total_notes}", True, WHITE)
        self.screen.blit(notes_text, (SCREEN_WIDTH - 150, 10))
        
        judgement_text = self.font_small.render(
            f"P: {self.judgements['PERFECT']} | G: {self.judgements['GOOD']} | O: {self.judgements['OK']} | M: {self.judgements['MISS']}",
            True, WHITE
        )
        self.screen.blit(judgement_text, (SCREEN_WIDTH - 300, 40))
        
        time_text = self.font_small.render(f"Time: {self.elapsed_time:.1f} / {self.song_end_time:.1f}s", True, WHITE)
        self.screen.blit(time_text, (10, 70))

    def draw_judgement(self):
        if self.current_judgement and time.time() - self.judgement_time < 0.5:
            color = WHITE
            if self.current_judgement == "PERFECT":
                color = LIGHT_BLUE
            elif self.current_judgement == "GOOD":
                color = (100, 255, 100)
            elif self.current_judgement == "OK":
                color = (255, 255, 100)
            elif self.current_judgement == "MISS":
                color = RED
                
            judgement_text = self.font_large.render(self.current_judgement, True, color)
            text_rect = judgement_text.get_rect(center=(SCREEN_WIDTH / 2, self.judgement_line_y - 40))
            self.screen.blit(judgement_text, text_rect)

    def update(self):
        if not self.is_playing:
            return
            
        current_time = time.time()
        self.elapsed_time = current_time - self.start_time

        for note in self.notes:
            if not note.hit:
                note.update(self.elapsed_time, self.note_speed, self.judgement_line_y)

                if note.y > self.judgement_line_y + 30:
                    note.hit = True
                    note.judgement = "MISS"
                    self.judgements["MISS"] += 1
                    self.combo = 0
                    self.show_judgement("MISS")
                    
        if self.elapsed_time >= self.song_end_time:
            pygame.mixer.music.stop()
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    def handle_key_press(self, key):
        if key == pygame.K_RETURN and not self.is_playing:
            self.start_game()
            return
        
        if key in KEYS:
            self.pressed_keys.add(key)
            self.key_pressed_time[key] = time.time()
            
            if self.is_playing:
                self.check_note_hit(KEYS[key])

    def handle_key_release(self, key):
        if key in KEYS and key in self.pressed_keys:
            self.pressed_keys.remove(key)

    def start_game(self):
        self.start_time = time.time()
        self.elapsed_time = 0
        self.is_playing = True
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.judgements = {"PERFECT": 0, "GOOD": 0, "OK": 0, "MISS": 0}
        
        for note in self.notes:
            note.hit = False
            note.judgement = None

        pygame.time.set_timer(pygame.USEREVENT, int(PREP_TIME * 1000), loops=1)

    def check_note_hit(self, track):
        current_time = time.time()
        game_time = current_time - self.start_time
         
        closest_note = None
        min_time_diff = float('inf')
        
        for note in self.notes:
            if note.track == track and not note.hit:
                time_diff = abs(note.time - game_time)
                
                if time_diff < OK_WINDOW and time_diff < min_time_diff:
                    closest_note = note
                    min_time_diff = time_diff
        
        if closest_note:
            closest_note.hit = True
            
            if min_time_diff <= PERFECT_WINDOW:
                closest_note.judgement = "PERFECT"
                self.judgements["PERFECT"] += 1
                self.score += int(MAX_SCORE / self.total_notes)
                self.combo += 1
                self.show_judgement("PERFECT")
            elif min_time_diff <= GOOD_WINDOW:
                closest_note.judgement = "GOOD"
                self.judgements["GOOD"] += 1
                self.score += int(MAX_SCORE / self.total_notes * GOOD_WEIGHT)
                self.combo += 1
                self.show_judgement("GOOD")
            elif min_time_diff <= OK_WINDOW:
                closest_note.judgement = "OK"
                self.judgements["OK"] += 1
                self.score += int(MAX_SCORE / self.total_notes * OK_WEIGHT)
                # self.combo += 1
                self.show_judgement("OK")
            
            if self.combo > self.max_combo:
                self.max_combo = self.combo

    def show_judgement(self, judgement):
        self.current_judgement = judgement
        self.judgement_time = time.time()

    def draw(self):
        self.draw_tracks()

        for note in self.notes:
            note.draw(self.screen)
        
        self.draw_judgement_line()
        self.draw_info()
        self.draw_judgement()
        
        if not self.is_playing:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            self.screen.blit(overlay, (0, 0))
            
            start_text = self.font_large.render("press ENTER to start", True, LIGHT_BLUE)
            text_rect = start_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2))
            self.screen.blit(start_text, text_rect)
            
            keys_text = self.font_medium.render("A, S, D, SPACE, J, K, L", True, WHITE)
            keys_rect = keys_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 40))
            self.screen.blit(keys_text, keys_rect)
            
            title_text = self.font_large.render("Rhythm game DEMO by yoroko", True, LIGHT_BLUE)
            title_rect = title_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 60))
            self.screen.blit(title_text, title_rect)
        
        pygame.display.flip()

    def run(self):
        running = True
        music_started = False
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    else:
                        self.handle_key_press(event.key)
                elif event.type == pygame.KEYUP:
                    self.handle_key_release(event.key)
                elif event.type == pygame.USEREVENT and self.is_playing and not music_started:
                    pygame.mixer.music.play()
                    music_started = True
                    
            self.update()
            self.draw()
            self.clock.tick(self.fps)
        
        pygame.quit()

def main():
    game = RhythmGame()
    
    midi_file = MIDIFILE
    
    try:
        game.load_midi(midi_file)
    except:
        pygame.quit()
        return

        
        for note_data in default_notes:
            game.notes.append(Note(
                time=note_data["time"],
                track=note_data["track"]
            ))
        
        game.total_notes = len(game.notes)
        game.max_score = MAX_SCORE
    
    
    game.run()

if __name__ == "__main__":
    main()
