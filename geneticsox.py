import sox
import curses
import random
import os
import sys
import subprocess
from pathlib import Path
import time
import glob

class AudioGeneticAlgorithm:
    def __init__(self, parent_paths, output_dir="generations"):
        self.parents = parent_paths
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.generation = 0
        self.population_size = 12  # more offspring with 4 parents
        self.max_generations = 2
        self.survivors_per_gen = 3  # keep 3 survivors for more diversity
        
    def get_random_samples(self, folder_path, count=4):  # now gets 4 samples
        """pick random audio samples from a folder"""
        folder = Path(folder_path)
        audio_extensions = ['*.wav', '*.aif', '*.aiff', '*.flac']
        
        all_files = []
        for ext in audio_extensions:
            all_files.extend(folder.glob(ext))
            all_files.extend(folder.glob(ext.upper()))
        
        if len(all_files) < count:
            print(f"only found {len(all_files)} audio files, need at least {count}")
            return all_files
            
        selected = random.sample(all_files, count)
        return selected
        
    def maybe_add_wild_card(self, inputs_folder):
        """random chance to add a 5th sample to spice things up"""
        if random.random() < 0.2:  # 20% chance
            folder = Path(inputs_folder)
            audio_extensions = ['*.wav', '*.aif', '*.aiff', '*.flac']
            
            all_files = []
            for ext in audio_extensions:
                all_files.extend(folder.glob(ext))
                all_files.extend(folder.glob(ext.upper()))
            
            # exclude current parents
            available = [f for f in all_files if f not in self.parents]
            
            if available:
                wild_card = random.choice(available)
                print(f"wild card enters: {wild_card.name}")
                self.parents.append(wild_card)
                return True
        return False

    def crossover_interleave(self, parent1_path, parent2_path, output_path):
        """enhanced crossover with automation effects"""
        info1 = sox.file_info.info(parent1_path)
        info2 = sox.file_info.info(parent2_path)
        
        print(f"  crossover: {Path(parent1_path).name} + {Path(parent2_path).name}")
        
        segments = []
        temp_dir = self.output_dir / "temp"
        temp_dir.mkdir(exist_ok=True)
        
        target_sample_rate = max(info1['sample_rate'], info2['sample_rate'])
        
        pos1 = 0
        pos2 = 0
        current_parent = 0
        segment_num = 0
        target_segments = random.randint(6, 15)
        
        try:
            for i in range(target_segments):
                if random.random() < 0.8:
                    current_parent = 1 - current_parent
                
                segment_type = random.random()
                if segment_type < 0.4:
                    segment_length = random.uniform(0.005, 0.03)
                elif segment_type < 0.8:
                    segment_length = random.uniform(0.03, 0.12)
                else:
                    segment_length = random.uniform(0.12, 0.5)
                
                if current_parent == 0:
                    parent_path = parent1_path
                    current_pos = pos1
                    parent_duration = info1['duration']
                    parent_name = "1"
                else:
                    parent_path = parent2_path
                    current_pos = pos2
                    parent_duration = info2['duration']
                    parent_name = "2"
                
                safe_end = parent_duration - 0.01
                if current_pos >= safe_end:
                    continue
                
                desired_end = current_pos + segment_length
                actual_end = min(desired_end, safe_end)
                actual_duration = actual_end - current_pos
                
                if actual_duration < 0.005:
                    continue
                
                print(f"    seg {len(segments)+1}: p{parent_name}, {actual_duration:.3f}s")
                
                try:
                    seg_path = temp_dir / f"seg_{segment_num}.wav"
                    cmd = f"sox '{parent_path}' '{seg_path}' trim {current_pos:.6f} {actual_duration:.6f}"
                    effects = []
                    
                    # pitch automation (40% chance)
                    if random.random() < 0.4:
                        automation_type = random.choice(['sweep_up', 'sweep_down', 'wobble'])
                        
                        if automation_type == 'sweep_up':
                            start_pitch = 0
                            end_pitch = random.uniform(300, 800)
                            effects.append(f"pitch {start_pitch}")
                            effects.append(f"pitch {(end_pitch - start_pitch) * 0.5}")
                            print(f"      pitch sweep up: 0 to {end_pitch:+.0f} cents")
                            
                        elif automation_type == 'sweep_down':
                            start_pitch = random.uniform(300, 600)
                            end_pitch = 0
                            effects.append(f"pitch {start_pitch}")
                            effects.append(f"pitch {-(start_pitch * 0.5)}")
                            print(f"      pitch sweep down: {start_pitch:+.0f} to 0 cents")
                            
                        else:  # wobble
                            wobble_rate = random.uniform(2, 8)
                            wobble_depth = random.uniform(100, 400)
                            effects.append(f"pitch {wobble_depth}")
                            effects.append(f"tremolo {wobble_rate}")
                            print(f"      pitch wobble: {wobble_depth:+.0f} cents at {wobble_rate:.1f}hz")
                    
                    # fades (60% chance)
                    if random.random() < 0.6:
                        fade_type = random.choice(['in', 'out', 'both'])
                        fade_duration = min(actual_duration * 0.3, 0.1)
                        
                        if fade_type == 'in':
                            effects.append(f"fade {fade_duration}")
                            print(f"      fade in: {fade_duration:.3f}s")
                        elif fade_type == 'out':
                            effects.append(f"fade 0 {actual_duration} {fade_duration}")
                            print(f"      fade out: {fade_duration:.3f}s")
                        else:  # both
                            effects.append(f"fade {fade_duration} {actual_duration} {fade_duration}")
                            print(f"      fade both: {fade_duration:.3f}s")
                    
                    # regular pitch shifts (70% chance)
                    if random.random() < 0.7:
                        pitch_choices = [
                            random.uniform(-800, -200),
                            random.uniform(-200, -50),
                            random.uniform(50, 200),
                            random.uniform(200, 800)
                        ]
                        pitch = random.choice(pitch_choices)
                        effects.append(f"pitch {pitch}")
                        print(f"      pitch: {pitch:+.0f} cents")
                    
                    # tempo changes (60% chance)
                    if random.random() < 0.6:
                        tempo = random.choice([0.5, 0.7, 0.8, 1.2, 1.5, 2.0])
                        effects.append(f"tempo {tempo}")
                        print(f"      tempo: {tempo}x")
                    
                    # reverb (50% chance)
                    if random.random() < 0.5:
                        reverb = random.uniform(20, 60)
                        effects.append(f"reverb {reverb}")
                        print(f"      reverb")
                    
                    # echo (40% chance)
                    if random.random() < 0.4:
                        delay = random.uniform(50, 200)
                        decay = random.uniform(0.3, 0.6)
                        effects.append(f"echo 0.8 0.88 {delay} {decay}")
                        print(f"      echo")
                    
                    # tremolo (30% chance)
                    if random.random() < 0.3:
                        rate = random.uniform(5, 15)
                        effects.append(f"tremolo {rate}")
                        print(f"      tremolo")
                    
                    # gain variations (70% chance)
                    if random.random() < 0.7:
                        gain = random.uniform(-4, 4)
                        effects.append(f"gain {gain}")
                        print(f"      gain: {gain:+.1f}db")
                    
                    # reverse (10% chance)
                    if random.random() < 0.1:
                        effects.append("reverse")
                        print(f"      reversed")
                    
                    effects.append(f"rate {target_sample_rate}")
                    
                    if effects:
                        cmd += f" {' '.join(effects)}"
                    
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    
                    if result.returncode == 0 and seg_path.exists() and seg_path.stat().st_size > 100:
                        segments.append(str(seg_path))
                        print(f"      mutant #{len(segments)}")
                        
                        if current_parent == 0:
                            pos1 = actual_end
                        else:
                            pos2 = actual_end
                    else:
                        print(f"      sox failed: {result.stderr}")
                            
                except Exception as e:
                    print(f"      error: {e}")
                
                segment_num += 1
            
            # combine segments
            if len(segments) >= 2:
                stereo_segments = []
                for i, seg in enumerate(segments):
                    stereo_path = temp_dir / f"stereo_{i}.wav"
                    cmd = f"sox '{seg}' '{stereo_path}' channels 2 rate {target_sample_rate}"
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    
                    if result.returncode == 0 and Path(stereo_path).exists():
                        stereo_segments.append(str(stereo_path))
                
                if len(stereo_segments) >= 2:
                    input_files = " ".join(f"'{f}'" for f in stereo_segments)
                    cmd = f"sox {input_files} '{output_path}'"
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    
                    if result.returncode == 0 and Path(output_path).exists():
                        print(f"    success: {Path(output_path).name}")
                        return True
            
            return False
            
        except Exception as e:
            print(f"    major error: {e}")
            return False
            
        finally:
            try:
                for seg_path in temp_dir.glob("*.wav"):
                    seg_path.unlink()
            except:
                pass

    def select_survivors(self, generation, gen_num):
        """select the fittest offspring to continue evolution"""
        print(f"\nnatural selection - gen {gen_num}")
        print(f"   selecting {self.survivors_per_gen} survivors from {len(generation)} offspring...")
        
        valid_offspring = []
        for offspring in generation:
            if Path(offspring).exists() and Path(offspring).stat().st_size > 1000:
                valid_offspring.append(offspring)
        
        if len(valid_offspring) < self.survivors_per_gen:
            print(f"   only {len(valid_offspring)} valid offspring, using all")
            return valid_offspring
        
        selection_method = random.choice(['random', 'size_based', 'duration_based'])
        
        if selection_method == 'random':
            survivors = random.sample(valid_offspring, self.survivors_per_gen)
            print(f"   random selection")
            
        elif selection_method == 'size_based':
            sizes = [(f, Path(f).stat().st_size) for f in valid_offspring]
            sizes.sort(key=lambda x: abs(x[1] - 50000))
            survivors = [f[0] for f in sizes[:self.survivors_per_gen]]
            print(f"   size-based selection")
            
        elif selection_method == 'duration_based':
            durations = []
            for f in valid_offspring:
                try:
                    info = sox.file_info.info(f)
                    durations.append((f, info['duration']))
                except:
                    durations.append((f, 0))
            durations.sort(key=lambda x: abs(x[1] - 1.0))
            survivors = [f[0] for f in durations[:self.survivors_per_gen]]
            print(f"   duration-based selection")
        
        for i, survivor in enumerate(survivors):
            print(f"   survivor {i+1}: {Path(survivor).name}")
            
        return survivors

    def create_generation(self, parents, gen_num):
        """create offspring and continue evolution"""
        if gen_num > self.max_generations:
            return parents
            
        new_generation = []
        gen_dir = self.output_dir / f"gen_{gen_num}"
        gen_dir.mkdir(exist_ok=True)
        
        print(f"\ngeneration {gen_num} - creating offspring from {len(parents)} parents:")
        for i, parent in enumerate(parents):
            print(f"   parent {i+1}: {Path(parent).name}")
        
        offspring_count = 0
        # crossbreed all combinations of parents
        for i in range(len(parents)):
            for j in range(i + 1, len(parents)):
                num_offspring = random.randint(1, 2)  # fewer offspring per pair with more parents
                
                for k in range(num_offspring):
                    offspring_path = gen_dir / f"child_{i}_{j}_{k}.wav"
                    print(f"  child {offspring_count + 1}: {Path(parents[i]).name} x {Path(parents[j]).name}")
                    
                    if self.crossover_interleave(parents[i], parents[j], offspring_path):
                        new_generation.append(offspring_path)
                        offspring_count += 1
                    
                    if len(new_generation) >= self.population_size:
                        break
                if len(new_generation) >= self.population_size:
                    break
            if len(new_generation) >= self.population_size:
                break
        
        print(f"gen {gen_num} results: {len(new_generation)} successful offspring")
        
        if gen_num < self.max_generations:
            survivors = self.select_survivors(new_generation, gen_num)
            if len(survivors) >= 2:
                return self.create_generation(survivors, gen_num + 1)
            else:
                print(f"not enough survivors, ending evolution at gen {gen_num}")
                return new_generation
        else:
            return new_generation

    def run_evolution(self):
        """run the complete evolutionary process"""
        print("starting multi-generational audio evolution...")
        print(f"target: {self.max_generations} generations, {self.survivors_per_gen} survivors per gen")
        
        parents = self.parents
        print(f"\ngen 0: {len(parents)} original parents")
        for i, parent in enumerate(parents):
            print(f"   parent {i+1}: {Path(parent).name}")
        
        final_generation = self.create_generation(parents, 1)
        
        print(f"\nevolution complete! final generation has {len(final_generation)} offspring")
        return final_generation

def main():
    inputs_folder = "./inputs"
    
    if not Path(inputs_folder).exists():
        print(f"{inputs_folder} folder not found!")
        print("create an 'inputs' folder and put some audio files in it.")
        return
    
    print("randomly selecting audio samples from inputs folder...")
    
    ga = AudioGeneticAlgorithm([])
    
    # get 4 samples for 2 pairs
    selected_samples = ga.get_random_samples(inputs_folder, 4)
    
    if len(selected_samples) < 4:
        print("need at least 4 audio files in inputs folder!")
        return
    
    ga.parents = selected_samples
    
    print("selected breeding group:")
    print("pair 1:")
    print(f"   parent 1: {ga.parents[0].name}")
    print(f"   parent 2: {ga.parents[1].name}")
    print("pair 2:")
    print(f"   parent 3: {ga.parents[2].name}")
    print(f"   parent 4: {ga.parents[3].name}")
    
    # maybe add wild card
    ga.maybe_add_wild_card(inputs_folder)
    
    offspring = ga.run_evolution()
    
    print(f"\nfinal generation {ga.max_generations}:")
    for i, child in enumerate(offspring):
        print(f"  {i+1}. {child}")
    print(f"\nplay them to hear {ga.max_generations} generations of genetic audio evolution!")
    print("run again for different random selections!")

if __name__ == "__main__":
    main()
