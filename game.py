import turtle
import queue
import random
import csv
import time
import winsound as ws
import subprocess
import threading
import os

class GameInitialisation:
    """ Class that initialises all game and game window attributes. Contains all variables that may be changed """
    def __init__(self):

        # Filenames
        self._other_sprites_file = "other_sprites.txt"
        self._normal_items_stats = "game_items_stats.csv"
        self._stress_items_stats = "stress_items_stats.csv"
        self._bonus_items_stats = "bonus_items_stats.csv"

        # Filepath for playing of sound effects
        self._pathname = os.getcwd()
        self._item_break_file = "ItemBreaking.wav"
        self._item_pickup_file = "ItemPickup.wav"

        # Powershell commands to play sound effects
        filepath1 = os.path.join(self._pathname, self._item_break_file)
        filepath2 = os.path.join(self._pathname, self._item_pickup_file)
        self._pwrshell_break_sound = f'[System.Media.SoundPlayer]::new("{filepath1}").PlaySync()'
        self._pwrshell_pickup_sound = f'[System.Media.SoundPlayer]::new("{filepath2}").PlaySync()'

        # Initialise game screen attributes
        self._screen = None
        self._screen_width = 1280
        self._screen_height = 720
        self._title = "SUTD Side-Scrolling Game"

        # Set player-related constants
        self._player_sprite = "Player"
        self._player_x_padding = 50
        self._player_y_padding = 75
        self._player_speed = 4
        self._player_start_xcor = -400

        # Number of frames for one full player animation cycle
        self._player_animation_rate = 48

        # Max FPS for game
        self._game_fps = 120

        # Spawn rate (number of frames) for items
        self._item_spawn_rate = None
        self._normal_spawn_rate = 50
        self._event_spawn_rate = 30
        self._bonus_spawn_rate = 10

        # Starting x coordinate for spawning items
        self._item_start_xcor = self._screen_width / 2 + 50
        
        # Game stats
        self._max_stat_value = 100
        self._game_stats = {"Stress": 0, "Health": self._max_stat_value, "Grades": 0}
        self._stat_low_threshold = 30
        self._stat_high_threshold = 70

        # Dictionaries containing the item data: x, y padding, stats increase/decrease
        self._normal_item_dict = {}
        self._stress_item_dict = {}
        self._bonus_item_dict = {}

        self._events_list = ["Rhino", "Mid Terms", "Recess", "Projects", "Finals"]

        self._instruction_screen_duration = 10000
        self._background_scroll_speed = 1

        self._sky_buffer = 350

        self._results_font = ('Consolas', 20, 'bold')
        self._stats_font = ('Consolas', 40, 'bold')
        self._instructions_font = ('Consolas', 30, 'bold')
        self._results_xcor = -270
        
    # Getters
    def get_screen_width(self):
        return self._screen_width
    
    def get_screen_height(self):
        return self._screen_height
    
    # Functions
    def initialise_screen(self):
        self._screen = turtle.Screen()
        turtle.tracer(0, 0)
        self._screen.title(self._title)
        self._screen.setup(width=self._screen_width, height=self._screen_height)

    def register_sprite_images(self):
        filename_list = [self._normal_items_stats, self._stress_items_stats, self._bonus_items_stats]
        dict_list = [self._normal_item_dict, self._stress_item_dict, self._bonus_item_dict]

        for filename, item_dict in zip(filename_list, dict_list):
            f = open(filename, 'r')
            csv_reader = list(csv.reader(f, delimiter=','))
            for row in csv_reader[1:]:
                turtle.register_shape(f"{row[0]}.gif")
                item_dict[row[0]] = [int(stat) for stat in row[1:]]
            f.close()
    
    def register_other_images(self):
        f = open(self._other_sprites_file, "r")
        names = f.readlines()

        for each_name in names:
            turtle.register_shape(each_name[:-1] + ".gif")
    
    def execute(self):
        # Set up the screen
        self.initialise_screen()

        # Register images used in game
        self.register_sprite_images()
        self.register_other_images()
        

class TitleScreen(GameInitialisation):
    def __init__(self):
        super().__init__()

    def instruction_screen(self):
        self._screen.clear()
        self._screen.bgpic("Instructions_Page.gif")
        
        # Schedule the actual game start after the delay
        self._screen.ontimer(self.start_game, self._instruction_screen_duration)

    def start_game(self):
        self._screen.clear()
        game = GameController(self._player_sprite) # Create new game instance
        game.execute()

    def set_male(self):
        self._player_sprite = "Male"
        self.instruction_screen()

    def set_female(self):
        self._player_sprite = "Female"
        self.instruction_screen()

    def choose_char(self):
        self._screen.clear()
        self._screen.bgpic("Character_Selection_Page.gif")
        self._screen.onkeypress(self.set_female, "Right")
        self._screen.onkeypress(self.set_male, "Left")
        self._screen.listen()
    
    def execute(self):
        # Starts turtle screen instance
        super().execute()

        # ADD YOUR CODE HERE
        # Display game title screen
        self._screen.bgpic("Title_Screen.gif")

        # Wait for SPACE key to be pressed then start game
        self._screen.onkeypress(self.choose_char, "space")
        self._screen.listen()
        
        ws.PlaySound('Main Menu.wav', ws.SND_ASYNC + ws.SND_LOOP + ws.SND_FILENAME)

        # Necessary to prevent Turtle from closing
        input("")


class GameController(GameInitialisation):
    """ 
    Class containing all functions related to the game flow and logic 
    Inherits from GameInitialisation to access window and game related attributes 
    """
    def __init__(self, character_option):
        super().__init__()

        self._player_sprite = character_option

        # Queue containing all objects currently alive, to be executed in that order 
        self._queue = queue.Queue(200)
        self._player = None

        # Attributes relating to the stage and progress of the game
        self._curr_stage = "Normal"
        self._curr_event = None
        self._game_ending = False

    # Getters
    def get_game_fps(self):
        return self._game_fps

    # Functions / Procedures
    def check_collision(self, object1, object2):
        # Get the range of x, y coordinates of the two objects
        obj_1_x_range = range(int(object1.get_xcor() - object1.get_x_padding()), int(object1.get_xcor() + object1.get_x_padding() + 1))
        obj_2_x_range = range(int(object2.get_xcor() - object2.get_x_padding()), int(object2.get_xcor() + object2.get_x_padding() + 1))
        obj_1_y_range = range(int(object1.get_ycor() - object1.get_y_padding()), int(object1.get_ycor() + object1.get_y_padding() + 1))
        obj_2_y_range = range(int(object2.get_ycor() - object2.get_y_padding()), int(object2.get_ycor() + object2.get_y_padding() + 1))
        x_range_same = None
        y_range_same = None
        
        # Check if any of the x, y coordinate overlap
        for i in obj_1_x_range:
            if i in obj_2_x_range:
                x_range_same = True
                break
        for j in obj_1_y_range:
            if j in obj_2_y_range:
                y_range_same = True
                break
            
        # If the x and y coordinate overlaps the object collides
        return x_range_same and y_range_same

    def spawn_random_item(self):
        # Spawns random items based on the current stage of the game
        if self._curr_stage == "Normal":
            item_list = list(self._normal_item_dict.keys())
            item_name = random.choice(item_list)
            item_data = self._normal_item_dict[item_name]

        elif self._curr_stage == "Event":
            match self._curr_event:
                case "Rhino":
                    item_name = "Rhino"
                    item_data = self._stress_item_dict[item_name]

                case "Mid Terms" | "Finals":
                    item_name = "Exam"
                    item_data = self._stress_item_dict[item_name]

                case "Recess":
                    item_list = list(self._bonus_item_dict.keys())
                    item_name = random.choice(item_list)
                    item_data = self._bonus_item_dict[item_name]

                case "Projects":
                    item_name = random.choice(["1DProject", "2DProject"])
                    item_data = self._stress_item_dict[item_name]

                case _:
                    return
        else:
            return

        # Instantiate the item and add it to the queue
        self._queue.put(Item(self, self._item_start_xcor, item_name, item_data))
    
    def listen_for_keypress(self):
        # Listen for keypress/release; used to move the player
        self._screen.onkeypress(self._player.up_pressed, "Up")
        self._screen.onkeypress(self._player.down_pressed, "Down")
        self._screen.onkeypress(self._player.right_pressed, "Right")
        self._screen.onkeypress(self._player.left_pressed, "Left")
        self._screen.onkeyrelease(self._player.up_released, "Up")
        self._screen.onkeyrelease(self._player.down_released, "Down")
        self._screen.onkeyrelease(self._player.right_released, "Right")
        self._screen.onkeyrelease(self._player.left_released, "Left")
        self._screen.listen()

    def display_stats_icons(self):
        # Create turtle for each stat icon
        grades = turtle.Turtle()
        grades.speed(0)
        grades.penup()
        grades.shape(f"Grades.gif")
        grades.setx(- (self._screen_width / 2) + 50)
        grades.sety((self._screen_height / 2) - 40)

        health = turtle.Turtle()
        health.shape(f"Health.gif")
        health.speed(0)
        health.penup()
        health.setx(- (self._screen_width / 2) + 50)
        health.sety((self._screen_height / 2) - 110)

        stress = turtle.Turtle()
        stress.shape(f"Stress.gif")
        stress.speed(0)
        stress.penup()
        stress.setx(- (self._screen_width / 2) + 50)
        stress.sety((self._screen_height / 2) - 180)

    def play_breaking_sound(self):
        subprocess.run(['powershell', '-Command', self._pwrshell_break_sound])

    def play_pickup_sound(self):
        subprocess.run(['powershell', '-Command', self._pwrshell_pickup_sound])

    def update_stats_display(self, stats_turtle):
        stats_turtle.clear()
        stats_turtle.speed(0)
        stats_turtle.penup()
        stats_turtle.hideturtle()
        stats_turtle.color("navy")
        stats_turtle.setx(- (self._screen_width / 2) + 100)
        stats_turtle.sety((self._screen_height / 2) - 72)
        stats_turtle.write(self._game_stats["Grades"], False, align='left', font=self._stats_font)
        stats_turtle.sety((self._screen_height / 2) - 142)
        stats_turtle.write(self._game_stats["Health"], False, align='left', font=self._stats_font)
        stats_turtle.sety((self._screen_height / 2) - 212)
        stats_turtle.write(self._game_stats["Stress"], False, align='left', font=self._stats_font)

    def show_instructions(self, instruction_turtle, next_event):
        instruction_turtle.speed(0)
        instruction_turtle.penup()
        instruction_turtle.hideturtle()
        instruction_turtle.color("maroon")
        instruction_turtle.setx(0)
        instruction_turtle.sety((self._screen_height / 2) - 100)
        if next_event == "Recess":
            instruction_turtle.color("navy")
            instruction_turtle.write("Bonus Event! It's recess week!\nCollect all the items!", False, align='center', font=self._instructions_font)
        else:
            instruction_turtle.color("maroon")
            instruction_turtle.write(f"Oh no, {next_event} ahead!\nAvoid all the stress!", False, align='center', font=self._instructions_font)

    def hide_instructions(self, instructions_turtle):
        instructions_turtle.clear()

    # Execute
    def execute(self):
        super().execute()
        
        # Add objects to queue
        self._queue.put(Display())
        self._queue.put(Delay(self))
        self._queue.put(Background(self, 1))
        self._queue.put(Background(self, 2))

        self._player = Player(self)
        self._queue.put(self._player)

        self.display_stats_icons()
        stats_turtle = turtle.Turtle()
        self.update_stats_display(stats_turtle)
        instructions_turtle = turtle.Turtle()
        self.show_instructions(instructions_turtle, None)
        
        # Starts taking in inputs from user to control the player
        self.listen_for_keypress()
        
        # Counter for number of frames generated and seconds passed
        frames = 0
        seconds = 0

        # Run the game loop while game hasn't end
        while True:
            while not self._queue.empty():
                
                nxt_obj = self._queue.get()
                
                if type(nxt_obj) == Display:
                    # Display object is executed once every frame 

                    # One cycle animation cycle for player has 4 frames/stages
                    if frames % (self._player_animation_rate // 4) == 0:
                        self._player.update_frame((frames // (self._player_animation_rate // 4)) % 4)

                    if frames % self._game_fps == 0:
                        # The following runs once every second
                        match seconds % 30:
                            # Event cycle repeats every 30 seconds
                            case 0:
                                self.hide_instructions(instructions_turtle)

                                # End game after finals or start the normal stage
                                if self._curr_event == "Finals":
                                    ws.PlaySound(None,ws.SND_PURGE)
                                    ws.PlaySound('Ending.wav', ws.SND_ASYNC + ws.SND_LOOP + ws.SND_FILENAME)
                                    self._game_ending = True
                                
                                else:
                                    self._curr_stage = "Normal"
                                    self._item_spawn_rate = self._normal_spawn_rate
                                    ws.PlaySound(None,ws.SND_PURGE)
                                    ws.PlaySound('Sakura.wav', ws.SND_ASYNC + ws.SND_FILENAME)

                            case 15:
                                # Transition to event stage. No items spawning at this point.
                                if self._curr_event == "Mid Terms":
                                    # Current event hasn't been updated at this point; 
                                    # So if the last event event is Mid Terms, start playing bonus stage music
                                    ws.PlaySound(None, ws.SND_PURGE) 
                                    ws.PlaySound('Bonus Event.wav', ws.SND_ASYNC + ws.SND_FILENAME)
                                    
                                else:
                                    ws.PlaySound(None, ws.SND_PURGE)
                                    ws.PlaySound('Event.wav', ws.SND_ASYNC + ws.SND_FILENAME)

                                self._curr_stage = "NormalTransition"
                                self._item_spawn_rate = 1
                                self.show_instructions(instructions_turtle, self._events_list[seconds // 30])

                            case 18:
                                # Start event stage
                                self._curr_stage = "Event"
                                self._item_spawn_rate = self._normal_spawn_rate
                                self._curr_event = self._events_list[seconds // 30]

                            case 28:
                                # Transition back to normal stage. No items spawning at this point.
                                self._curr_stage = "EventTransition"
                                self._item_spawn_rate = 1
                                
                        seconds += 1

                    # Show end screen if game ended and no more items left in queue
                    if self._game_ending and self._queue.qsize() == 4:
                        stats_turtle.clear()
                        ending_screen = EndScreen(self._game_stats)
                        ending_screen.execute()
                        return

                    # Spawn a random item based on the spawn rate
                    if frames % self._item_spawn_rate == 0 and not self._game_ending:
                        self.spawn_random_item()
                    
                    frames += 1

                # Execute code for next object
                result = nxt_obj.execute()

                # If type of object is Item
                if type(nxt_obj) == Item:
                    
                    # Check if Item collides with Player
                    collide_result = self.check_collision(self._player, nxt_obj)

                    # If item collides with Player
                    if collide_result == True:
                        # print(f"Player collided with {type(nxt_obj)} {nxt_obj} with name {nxt_obj.get_name()} at {nxt_obj.get_location()}.")
                        
                        if nxt_obj.get_name() in ["Crate1", "Crate2", "Crate3", "Rhino"]:
                            play_thread = threading.Thread(target=self.play_breaking_sound)
                            play_thread.start()
                        else:
                            play_thread = threading.Thread(target=self.play_pickup_sound)
                            play_thread.start()

                        # Update game stats
                        self._game_stats["Stress"] += nxt_obj.get_stress()
                        self._game_stats["Health"] += nxt_obj.get_health()
                        self._game_stats["Grades"] += nxt_obj.get_grades()

                        self._game_stats["Stress"] = max(min(self._game_stats["Stress"],100), 0)
                        self._game_stats["Health"] = max(min(self._game_stats["Health"],100), 0)
                        self._game_stats["Grades"] = max(min(self._game_stats["Grades"],100), 0)
                        
                        # print(self._game_stats)
                            
                        # Updates the stat display
                        self.update_stats_display(stats_turtle)
                        
                        # Kill Item instance
                        result = False

                # If execute function returns True, object will be added back to queue
                if result:
                    self._queue.put(nxt_obj)
                else:
                    nxt_obj.kill()

class Sprite:
    """ Class containing all basic attributes and functions related to sprites(moving images)"""
    def __init__(self, controller):
        self._controller = controller
        self._alive = True

        # Turtle initialisations
        self._obj = turtle.Turtle()
        self._obj.speed(0)
        self._obj.penup()

        # Will be defined in subclasses
        self._speed = None
        self._x_padding = None
        self._y_padding = None

    def get_speed(self):
        return self._speed
    
    def is_alive(self):
        return self._alive
    
    def get_xcor(self):
        return self._obj.xcor()
    
    def get_ycor(self):
        return self._obj.ycor()
    
    def get_x_padding(self):
        return self._x_padding
    
    def get_y_padding(self):
        return self._y_padding
    
    def get_location(self):
        return (self._obj.xcor(), self._obj.ycor())


class Background(Sprite):
    """ Class for the background image, 2 background sprites are used to create the baclground scrolling effect"""
    def __init__(self, controller, number):
        super().__init__(controller)

        self._obj.shape("Background.gif")

        # Set initial position of background
        if number == 1:
            self._obj.setx(0)
        elif number == 2:
            self._obj.setx(self._controller.get_screen_width())

        self._speed = self._controller._background_scroll_speed

    def move(self):
        # Teleports the background back to the right if the background is longer in the screen
        if self._obj.xcor() <= - self._controller.get_screen_width():
             self._obj.setx(self._controller.get_screen_width())

        # Moves the background
        self._obj.setx(self._obj.xcor() - self._speed)

    def execute(self):
        self.move()    
        return True


class Player(Sprite):
    """ Class containing all the attributes and functions related to the player sprite """
    def __init__(self, controller):
        super().__init__(controller)

        # Attributes whether up/down/left/right key is pressed
        self._up = False
        self._down = False
        self._left = False
        self._right = False

        self._x_padding = self._controller._player_x_padding
        self._y_padding = self._controller._player_y_padding

        self._speed = self._controller._player_speed

        self._speed_x = 0
        self._speed_y = 0

        self._alive = True

        # Turtle initialisations
        self._obj.shape(f"{self._controller._player_sprite}0.gif")
        self._obj.goto(self._controller._player_start_xcor, 0)

    def update_frame(self, frame_no):
        # Updates frame to create player animation
        self._obj.shape(f"{self._controller._player_sprite}{frame_no}.gif")

    def update_speed(self):
        """ Updates the speed based on what key is pressed. Allows for multiple keys to be pressed at the same time """
        # Resets speed to 0
        self._speed_x = 0
        self._speed_y = 0
        
        # Set speed according to what keys are pressed
        if self._up:
            self._speed_y += self._speed
        if self._down:
            self._speed_y -= self._speed
        if self._right:
            self._speed_x += self._speed
        if self._left:
            self._speed_x -= self._speed

    def move(self):
        # Teleports the player back within the screen if player goes out
        if self.get_ycor() - self.get_y_padding() > (self._controller.get_screen_height() / 2) - self._controller._sky_buffer:
            self._obj.sety((self._controller.get_screen_height() / 2) - self._controller._sky_buffer + self.get_y_padding())
            # print("Too High!")
        elif self.get_ycor() - self.get_y_padding() < (self._controller.get_screen_height()) / (-2):
            self._obj.sety(self.get_y_padding() - (self._controller.get_screen_height() / 2))
            # print("Too Low!")
            
        if self.get_xcor() + self.get_x_padding() > (self._controller.get_screen_width()) / 2:
            self._obj.setx((self._controller.get_screen_width() / 2) - self.get_x_padding())
            # print("Too Right!")
        elif self.get_xcor() - self.get_x_padding() < (self._controller.get_screen_width()) / (-2):
            self._obj.setx(self.get_x_padding() - (self._controller.get_screen_width() / 2))
            # print("Too Left!")

        # Teleports player to new position based on the speed
        self._obj.setx(self._obj.xcor() + self._speed_x)
        self._obj.sety(self._obj.ycor() + self._speed_y)

    # Checks is up/down/left/right key is pressed or released
    def up_pressed(self):
        self._up = True
        # print("up pressed")

    def up_released(self):
        self._up = False
        # print("up released")

    def down_pressed(self):
        self._down = True
        # print("down pressed")
        
    def down_released(self):
        self._down = False
        # print("down released")

    def left_pressed(self):
        self._left = True
        # print("left pressed")
        
    def left_released(self):
        self._left = False
        # print("left released")
    
    def right_pressed(self):
        self._right = True
        # print("right pressed")

    def right_released(self):
        self._right = False
        # print("right released")

    def execute(self):
        self.update_speed()
        self.move()
        return True


class Item(Sprite):
    """ Class containing attributes and functions relating to item sprites: crates, power-ups, obstacles, etc. """
    def __init__(self, controller, start_xcor, name, item_data):
        super().__init__(controller)
    
        self._name = name
        self._x_padding = item_data[0]
        self._y_padding = item_data[1]

        # Turtle initialisations
        self._obj.shape(f"{name}.gif")
        self._start_xcor = start_xcor

        # Game data
        self._stress = item_data[2]
        self._health = item_data[3]
        self._grades = item_data[4]
        self._base_speed = item_data[5]

        # Starting position
        self._obj.goto(
            # Start outside of screen
            self._start_xcor,
            # Randomise y coordinate of starting object position
            random.randint(
                (-self._controller.get_screen_height() // 2) + 30,
                (self._controller.get_screen_height() // 2) - 200
            )
        )

        # Randomise speed
        self._speed = random.randint(self._base_speed - 1, self._base_speed + 1)

    # Getters
    def get_name(self):
        return self._name
    
    def get_stress(self):
        return self._stress

    def get_health(self):
        return self._health
    
    def get_grades(self):
        return self._grades

    # Functions / Procedures
    def move(self):
        # Shift obstacle x coordinate by speed units
        self._obj.setx(self._obj.xcor() - self._speed)
        
    def is_out(self):
        # Check if x coordinate of obstacle is out of screen
        if (self._obj.xcor() < - (self._controller.get_screen_width() // 2 + self._x_padding + 10 )):
            # print(f"Object {self} out of screen.")
            return True
        else:
            return False
    
    def kill(self):
        """
        Not sure if this actually kills the object and takes it out of memory, or is the only way screen.clear()?
        screen.clear() would kill all other objects though :/
        """
        self._obj.clear()
        self._obj.hideturtle()
        del self._obj
        del self
        # print(f"Object {self} killed.")

    def execute(self):
        if self.is_out():
            return False
        else:
            self.move()
            return True


class Display:
    """ Updates the game display """
    def __init__(self):
        pass

    def execute(self):
        turtle.update()
        return True
    

class Delay:
    """ Normalises execution speed of game across different devices and ensures game is run at relatively constant speed """
    def __init__(self, controller):
        self._controller = controller
        self._prev_time = time.time()

    def execute(self):
        # Sleeps for remaining duration of frame
        # If one frame is set to 10 seconds and all other operations are completed in 7 seconds, delay sleeps for 3 seconds
        now = time.time()
        sleep_time = 1/self._controller.get_game_fps() - (now - self._prev_time)

        if sleep_time > 0:
            time.sleep(sleep_time)
            self._prev_time = now + sleep_time
        else:
            self._prev_time = now
        return True
        

class EndScreen(GameInitialisation):
    """ Class containing functions related to end screen """
    def __init__(self, final_game_stats):
        super().__init__()
        self._final_games_stats = final_game_stats

    def execute(self):
        # Starts turtle screen instance
        super().execute()
        
        # Display end screen
        self._screen.bgpic("Results_Page.gif")

        # 
        if self._final_games_stats["Stress"] > self._stat_high_threshold:
            scale1, stress_msg = 'high,', 'perhaps \nyou should take care of yourself mentally!'
        elif self._final_games_stats["Stress"] < self._stat_low_threshold:
            scale1, stress_msg = 'low,', '\ngood job maintaining it this low!'
        else:
            scale1, stress_msg = 'neutral,', '\nkeep it up!'

        if self._final_games_stats["Health"] > self._stat_high_threshold:
            scale2, health_msg = 'high,', 'well done! \nYou have taken care of your health well!'
        elif self._final_games_stats["Health"] < self._stat_low_threshold:
            scale2, health_msg = 'low,', 'perhaps \nyou should take care of yourself physically!'
        else:
            scale2, health_msg = 'neutral,', '\nkeep it up!'

        if self._final_games_stats["Grades"] > self._stat_high_threshold:
            scale3, grades_msg = 'high,', '\nand you got an A++, well done!'
        elif self._final_games_stats["Grades"] < self._stat_low_threshold:
            scale3, grades_msg = 'low,', 'perhaps balancing \nyour life and focusing on academics would help!'
        else:
            scale3, grades_msg = 'neutral,', '\nkeep it up!'

        test_turtle = turtle.Turtle()
        test_turtle.speed(0)
        test_turtle.setx(self._results_xcor)
        test_turtle.sety(-160)
        test_turtle.write('Your stress level is relatively {} {}'.format(scale1, stress_msg), False, align='left', font=self._results_font)
        test_turtle.sety(-30)
        test_turtle.write('Your health level is relatively {} {}'.format(scale2, health_msg), False, align='left',font=self._results_font)
        test_turtle.sety(80)
        test_turtle.write('Your grades are relatively {} {}'.format(scale3, grades_msg), False, align='left',font=self._results_font)

        turtle.exitonclick()

def main():
    title = TitleScreen()
    title.execute()
    
    
if __name__ == "__main__":
    main()