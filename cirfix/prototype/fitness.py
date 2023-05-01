import sys
import os

X_WEIGHT = 2
DEBUG = False

# remove '\n' or other white space from bitlist 
def strip_bits(bits):
    for i in range(len(bits)):
        bits[i] = bits[i].strip()
    return bits

# parse the weights file
def get_weights_static(weights_file, oracle):
    weights_by_varname = dict()
    weights_by_bit = dict()
    
    for line in weights_file:
        line = line.strip()
        tmp = line.split("=")
        weights_by_varname[tmp[0]] = float(tmp[1])
    
    bits = strip_bits(oracle[0].split(","))
    for i in range(1, len(bits)):
        varname = bits[i]
        if "[" in varname:
            varname = varname.split("[")[0]
        weights_by_bit[i] = weights_by_varname.get(varname)
    
    return weights_by_bit

# parse the weights file
# TODO: refactor this!
def get_weights_fuzz(weights_file, oracle):
    weights_by_varname = dict()
    weights_by_bit = dict()
    
    for line in weights_file:
        line = line.strip()
        tmp = line.split("=")
        weights_by_varname[tmp[0]] = float(tmp[1])

    print(weights_by_varname)
    
    bits = strip_bits(oracle[0].split(","))
    for i in range(1, len(bits)):
        varname = bits[i]
        weights_by_bit[i] = weights_by_varname.get(varname)
    
    return weights_by_bit

def resize_sim(oracle, sim):
    oracle_len = len(oracle)
    sim_len = len(sim)
    num_bits = len(oracle[0].split(",")) - 1
    if len(oracle) > 2:
        clk_len = float(oracle[2].split(",")[0]) - float(oracle[1].split(",")[0])
        last_clk = eval(oracle[oracle_len-1].split(",")[0])
    else:
        clk_len = 100 # arbirtray clk_len, doesn't matter anyways
        last_clk = 0
    
    if oracle_len > sim_len:
        for i in range(oracle_len-sim_len):
            tmp_str = str(last_clk + (i+1) * clk_len)
            for i in range(num_bits):
                tmp_str += ",x"
            tmp_str += "\n"
            sim.append(tmp_str)
    elif oracle_len < sim_len:
        for i in range(sim_len-oracle_len):
            sim.pop()

    return oracle, sim

def resize_clkcycle_outputs(tmp_oracle, tmp_sim):
    if len(tmp_oracle) > len(tmp_sim):
        diff = len(tmp_oracle) - len(tmp_sim)
        for i in range(diff):
            tmp_sim.append('x')
    else:
        diff = len(tmp_sim) - len(tmp_oracle)
        for i in range(diff):
            tmp_oracle.pop()

    return tmp_oracle, tmp_sim


def calculate_fitness(oracle, sim, weights_file, weighting):

    weights = None
    if weights_file and weighting == "static":
        weights = get_weights_static(weights_file, oracle)
    elif weights_file and weighting == "fuzz":
        weights = get_weights_fuzz(weights_file, oracle)
    print(weights)
    
    if len(oracle) != len(sim): 
        oracle, sim = resize_sim(oracle, sim)

    fitness = 0
    total_possible = 0 
    for i in range(1, len(oracle)):
        clk = oracle[i].split(",")[0]
        tmp_oracle = strip_bits(oracle[i].split(",")[1:])
        tmp_sim = strip_bits(sim[i].split(",")[1:])

        # cycle_weight = 1/(2**(i-1))
        cycle_weight = 1
        
        if len(tmp_oracle) != len(tmp_sim):
            tmp_oracle, tmp_sim = resize_clkcycle_outputs(tmp_oracle, tmp_sim)

        for b in range(len(tmp_oracle)):
            if weights:
                bit_weight = weights[b+1] # off-set by 1 since time not included in b
                if not bit_weight: bit_weight = 1 # if the bit weight was not present in the weights file (e.g. it never got an assignment)
            else:
                bit_weight = 1

            if (tmp_oracle[b], tmp_sim[b]) in (('0', '0'), ('1', '1')):
                fitness += bit_weight * cycle_weight * 1
                total_possible += bit_weight * cycle_weight * 1
            elif (tmp_oracle[b], tmp_sim[b]) in (('x', 'x'), ('z','z')):
                fitness += bit_weight * cycle_weight * X_WEIGHT * 1
                total_possible += bit_weight * cycle_weight * X_WEIGHT * 1
            elif (tmp_oracle[b], tmp_sim[b]) in (('0', '1'), ('1', '0')):
                if DEBUG: print("Mismatch in bit %s of clock cycle %s (at time %s)..." % (b, i, clk))
                fitness -= bit_weight * cycle_weight * 1
                total_possible += bit_weight * cycle_weight * 1
            elif (tmp_oracle[b], tmp_sim[b]) in (('0', 'x'), ('1', 'x'), ('x', '0'), ('x', '1'), ('0', 'z'), ('1', 'z'), ('z', '0'), ('z', '1'), ('z','x'), ('x','z')):
                if DEBUG: print("Mismatch in x or z-bit %s of clock cycle %s (at time %s)..." % (b, i, clk))
                fitness -= bit_weight * cycle_weight * X_WEIGHT * 1
                total_possible += bit_weight * cycle_weight * X_WEIGHT * 1

    return fitness, total_possible

def main():
    if len(sys.argv) != 3 and len(sys.argv) != 5:
        print("USAGE: python3 fitness.py <oracle.txt> <output.txt> [weights.txt] [fuzz|static]")
        sys.exit(1)

    f = open(sys.argv[1], "r")
    oracle_lines = f.readlines()
    f.close()

    f = open(sys.argv[2], "r")
    sim_lines = f.readlines()
    f.close()

    weights = None
    weighting = None
    if len(sys.argv) == 5:
        weighting = sys.argv[4]
        f = open(sys.argv[3], "r")
        weights = f.readlines()
        f.close()


    fitness, total_possible = calculate_fitness(oracle_lines, sim_lines, weights, weighting)
    ff = fitness/total_possible
    if ff < 0: ff = 0
    print(ff)

if __name__ == '__main__':
    main()
