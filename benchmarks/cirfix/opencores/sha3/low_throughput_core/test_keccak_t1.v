/*
 * Copyright 2013, Homer Hsing <homer.hsing@gmail.com>
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

`timescale 1ns / 1ps
`define P 20

module test_keccak;

    // Inputs
    reg clk;
    reg instrumented_clk;
    reg reset;
    reg [31:0] in;
    reg in_ready;
    reg is_last;
    reg [1:0] byte_num;

    // Outputs
    wire buffer_full;
    wire [511:0] out;
    wire out_ready;

    // Var
    integer i;

    integer f;

    // Instantiate the Unit Under Test (UUT)
    keccak uut (
        .clk(clk),
        .reset(reset),
        .in(in),
        .in_ready(in_ready),
        .is_last(is_last),
        .byte_num(byte_num),
        .buffer_full(buffer_full),
        .out(out),
        .out_ready(out_ready)
    );

    initial begin
      f = $fopen("output_test_keccak_t1.txt");
      $fwrite(f, "time,buffer_full,out[511],out[510],out[509],out[508],out[507],out[506],out[505],out[504],out[503],out[502],out[501],out[500],out[499],out[498],out[497],out[496],out[495],out[494],out[493],out[492],out[491],out[490],out[489],out[488],out[487],out[486],out[485],out[484],out[483],out[482],out[481],out[480],out[479],out[478],out[477],out[476],out[475],out[474],out[473],out[472],out[471],out[470],out[469],out[468],out[467],out[466],out[465],out[464],out[463],out[462],out[461],out[460],out[459],out[458],out[457],out[456],out[455],out[454],out[453],out[452],out[451],out[450],out[449],out[448],out[447],out[446],out[445],out[444],out[443],out[442],out[441],out[440],out[439],out[438],out[437],out[436],out[435],out[434],out[433],out[432],out[431],out[430],out[429],out[428],out[427],out[426],out[425],out[424],out[423],out[422],out[421],out[420],out[419],out[418],out[417],out[416],out[415],out[414],out[413],out[412],out[411],out[410],out[409],out[408],out[407],out[406],out[405],out[404],out[403],out[402],out[401],out[400],out[399],out[398],out[397],out[396],out[395],out[394],out[393],out[392],out[391],out[390],out[389],out[388],out[387],out[386],out[385],out[384],out[383],out[382],out[381],out[380],out[379],out[378],out[377],out[376],out[375],out[374],out[373],out[372],out[371],out[370],out[369],out[368],out[367],out[366],out[365],out[364],out[363],out[362],out[361],out[360],out[359],out[358],out[357],out[356],out[355],out[354],out[353],out[352],out[351],out[350],out[349],out[348],out[347],out[346],out[345],out[344],out[343],out[342],out[341],out[340],out[339],out[338],out[337],out[336],out[335],out[334],out[333],out[332],out[331],out[330],out[329],out[328],out[327],out[326],out[325],out[324],out[323],out[322],out[321],out[320],out[319],out[318],out[317],out[316],out[315],out[314],out[313],out[312],out[311],out[310],out[309],out[308],out[307],out[306],out[305],out[304],out[303],out[302],out[301],out[300],out[299],out[298],out[297],out[296],out[295],out[294],out[293],out[292],out[291],out[290],out[289],out[288],out[287],out[286],out[285],out[284],out[283],out[282],out[281],out[280],out[279],out[278],out[277],out[276],out[275],out[274],out[273],out[272],out[271],out[270],out[269],out[268],out[267],out[266],out[265],out[264],out[263],out[262],out[261],out[260],out[259],out[258],out[257],out[256],out[255],out[254],out[253],out[252],out[251],out[250],out[249],out[248],out[247],out[246],out[245],out[244],out[243],out[242],out[241],out[240],out[239],out[238],out[237],out[236],out[235],out[234],out[233],out[232],out[231],out[230],out[229],out[228],out[227],out[226],out[225],out[224],out[223],out[222],out[221],out[220],out[219],out[218],out[217],out[216],out[215],out[214],out[213],out[212],out[211],out[210],out[209],out[208],out[207],out[206],out[205],out[204],out[203],out[202],out[201],out[200],out[199],out[198],out[197],out[196],out[195],out[194],out[193],out[192],out[191],out[190],out[189],out[188],out[187],out[186],out[185],out[184],out[183],out[182],out[181],out[180],out[179],out[178],out[177],out[176],out[175],out[174],out[173],out[172],out[171],out[170],out[169],out[168],out[167],out[166],out[165],out[164],out[163],out[162],out[161],out[160],out[159],out[158],out[157],out[156],out[155],out[154],out[153],out[152],out[151],out[150],out[149],out[148],out[147],out[146],out[145],out[144],out[143],out[142],out[141],out[140],out[139],out[138],out[137],out[136],out[135],out[134],out[133],out[132],out[131],out[130],out[129],out[128],out[127],out[126],out[125],out[124],out[123],out[122],out[121],out[120],out[119],out[118],out[117],out[116],out[115],out[114],out[113],out[112],out[111],out[110],out[109],out[108],out[107],out[106],out[105],out[104],out[103],out[102],out[101],out[100],out[99],out[98],out[97],out[96],out[95],out[94],out[93],out[92],out[91],out[90],out[89],out[88],out[87],out[86],out[85],out[84],out[83],out[82],out[81],out[80],out[79],out[78],out[77],out[76],out[75],out[74],out[73],out[72],out[71],out[70],out[69],out[68],out[67],out[66],out[65],out[64],out[63],out[62],out[61],out[60],out[59],out[58],out[57],out[56],out[55],out[54],out[53],out[52],out[51],out[50],out[49],out[48],out[47],out[46],out[45],out[44],out[43],out[42],out[41],out[40],out[39],out[38],out[37],out[36],out[35],out[34],out[33],out[32],out[31],out[30],out[29],out[28],out[27],out[26],out[25],out[24],out[23],out[22],out[21],out[20],out[19],out[18],out[17],out[16],out[15],out[14],out[13],out[12],out[11],out[10],out[9],out[8],out[7],out[6],out[5],out[4],out[3],out[2],out[1],out[0],out_ready\n");
      forever begin
        @(posedge clk);
        $fwrite(f, "%g,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b,%b\n", $time,buffer_full,out[511],out[510],out[509],out[508],out[507],out[506],out[505],out[504],out[503],out[502],out[501],out[500],out[499],out[498],out[497],out[496],out[495],out[494],out[493],out[492],out[491],out[490],out[489],out[488],out[487],out[486],out[485],out[484],out[483],out[482],out[481],out[480],out[479],out[478],out[477],out[476],out[475],out[474],out[473],out[472],out[471],out[470],out[469],out[468],out[467],out[466],out[465],out[464],out[463],out[462],out[461],out[460],out[459],out[458],out[457],out[456],out[455],out[454],out[453],out[452],out[451],out[450],out[449],out[448],out[447],out[446],out[445],out[444],out[443],out[442],out[441],out[440],out[439],out[438],out[437],out[436],out[435],out[434],out[433],out[432],out[431],out[430],out[429],out[428],out[427],out[426],out[425],out[424],out[423],out[422],out[421],out[420],out[419],out[418],out[417],out[416],out[415],out[414],out[413],out[412],out[411],out[410],out[409],out[408],out[407],out[406],out[405],out[404],out[403],out[402],out[401],out[400],out[399],out[398],out[397],out[396],out[395],out[394],out[393],out[392],out[391],out[390],out[389],out[388],out[387],out[386],out[385],out[384],out[383],out[382],out[381],out[380],out[379],out[378],out[377],out[376],out[375],out[374],out[373],out[372],out[371],out[370],out[369],out[368],out[367],out[366],out[365],out[364],out[363],out[362],out[361],out[360],out[359],out[358],out[357],out[356],out[355],out[354],out[353],out[352],out[351],out[350],out[349],out[348],out[347],out[346],out[345],out[344],out[343],out[342],out[341],out[340],out[339],out[338],out[337],out[336],out[335],out[334],out[333],out[332],out[331],out[330],out[329],out[328],out[327],out[326],out[325],out[324],out[323],out[322],out[321],out[320],out[319],out[318],out[317],out[316],out[315],out[314],out[313],out[312],out[311],out[310],out[309],out[308],out[307],out[306],out[305],out[304],out[303],out[302],out[301],out[300],out[299],out[298],out[297],out[296],out[295],out[294],out[293],out[292],out[291],out[290],out[289],out[288],out[287],out[286],out[285],out[284],out[283],out[282],out[281],out[280],out[279],out[278],out[277],out[276],out[275],out[274],out[273],out[272],out[271],out[270],out[269],out[268],out[267],out[266],out[265],out[264],out[263],out[262],out[261],out[260],out[259],out[258],out[257],out[256],out[255],out[254],out[253],out[252],out[251],out[250],out[249],out[248],out[247],out[246],out[245],out[244],out[243],out[242],out[241],out[240],out[239],out[238],out[237],out[236],out[235],out[234],out[233],out[232],out[231],out[230],out[229],out[228],out[227],out[226],out[225],out[224],out[223],out[222],out[221],out[220],out[219],out[218],out[217],out[216],out[215],out[214],out[213],out[212],out[211],out[210],out[209],out[208],out[207],out[206],out[205],out[204],out[203],out[202],out[201],out[200],out[199],out[198],out[197],out[196],out[195],out[194],out[193],out[192],out[191],out[190],out[189],out[188],out[187],out[186],out[185],out[184],out[183],out[182],out[181],out[180],out[179],out[178],out[177],out[176],out[175],out[174],out[173],out[172],out[171],out[170],out[169],out[168],out[167],out[166],out[165],out[164],out[163],out[162],out[161],out[160],out[159],out[158],out[157],out[156],out[155],out[154],out[153],out[152],out[151],out[150],out[149],out[148],out[147],out[146],out[145],out[144],out[143],out[142],out[141],out[140],out[139],out[138],out[137],out[136],out[135],out[134],out[133],out[132],out[131],out[130],out[129],out[128],out[127],out[126],out[125],out[124],out[123],out[122],out[121],out[120],out[119],out[118],out[117],out[116],out[115],out[114],out[113],out[112],out[111],out[110],out[109],out[108],out[107],out[106],out[105],out[104],out[103],out[102],out[101],out[100],out[99],out[98],out[97],out[96],out[95],out[94],out[93],out[92],out[91],out[90],out[89],out[88],out[87],out[86],out[85],out[84],out[83],out[82],out[81],out[80],out[79],out[78],out[77],out[76],out[75],out[74],out[73],out[72],out[71],out[70],out[69],out[68],out[67],out[66],out[65],out[64],out[63],out[62],out[61],out[60],out[59],out[58],out[57],out[56],out[55],out[54],out[53],out[52],out[51],out[50],out[49],out[48],out[47],out[46],out[45],out[44],out[43],out[42],out[41],out[40],out[39],out[38],out[37],out[36],out[35],out[34],out[33],out[32],out[31],out[30],out[29],out[28],out[27],out[26],out[25],out[24],out[23],out[22],out[21],out[20],out[19],out[18],out[17],out[16],out[15],out[14],out[13],out[12],out[11],out[10],out[9],out[8],out[7],out[6],out[5],out[4],out[3],out[2],out[1],out[0],out_ready);
      end
    end

    initial begin
        // Initialize Inputs
        clk = 0;
        instrumented_clk = 0;
        reset = 0;
        in = 0;
        in_ready = 0;
        is_last = 0;
        byte_num = 0;

        // Wait 100 ns for global reset to finish
        #100;

        // Add stimulus here
        @ (negedge clk);

        // SHA3-512("The quick brown fox jumps over the lazy dog")
        reset = 1; #(`P); reset = 0;
        in_ready = 1; is_last = 0;
        in = "The "; #(`P);
        in = "quic"; #(`P);
        in = "k br"; #(`P);
        in = "own "; #(`P);
        in = "fox "; #(`P);
        in = "jump"; #(`P);
        in = "s ov"; #(`P);
        in = "er t"; #(`P);
        in = "he l"; #(`P);
        in = "azy "; #(`P);
        in = "dog "; byte_num = 3; is_last = 1; #(`P); /* !!! not in = "dog" */
        in_ready = 0; is_last = 0;
        while (out_ready !== 1)
            #(`P);
        check(512'hd135bb84d0439dbac432247ee573a23ea7d3c9deb2a968eb31d47c4fb45f1ef4422d6c531b5b9bd6f449ebcc449ea94d0a8f05f62130fda612da53c79659f609);

        // SHA3-512("The quick brown fox jumps over the lazy dog.")
        reset = 1; #(`P); reset = 0;
        in_ready = 1; is_last = 0;
        in = "The "; #(`P);
        in = "quic"; #(`P);
        in = "k br"; #(`P);
        in = "own "; #(`P);
        in = "fox "; #(`P);
        in = "jump"; #(`P);
        in = "s ov"; #(`P);
        in = "er t"; #(`P);
        in = "he l"; #(`P);
        in = "azy "; #(`P);
        in = "dog."; #(`P);
        in = 0; byte_num = 0; is_last = 1; #(`P); /* !!! */
        in_ready = 0; is_last = 0;
        while (out_ready !== 1)
            #(`P);
        check(512'hab7192d2b11f51c7dd744e7b3441febf397ca07bf812cceae122ca4ded6387889064f8db9230f173f6d1ab6e24b6e50f065b039f799f5592360a6558eb52d760);

        // hash an string "\xA1\xA2\xA3\xA4\xA5", len == 5
        reset = 1; #(`P); reset = 0;
        #(7*`P); // wait some cycles
        in_ready = 1; is_last = 0; byte_num = 1;
        in = 32'hA1A2A3A4;
        #(`P);
        is_last = 1; byte_num = 1;
        in = 32'hA5000000;
        #(`P);
        in = 32'h12345678; // next input
        in_ready = 1;
        is_last = 1;
        #(`P/2);
        if (buffer_full === 1) error; // should be 0
        #(`P/2);
        in_ready = 0;
        is_last = 0;

        while (out_ready !== 1)
            #(`P);
        check(512'h12f4a85b68b091e8836219e79dfff7eb9594a42f5566515423b2aa4c67c454de83a62989e44b5303022bfe8c1a9976781b747a596cdab0458e20d8750df6ddfb);
        for(i=0; i<5; i=i+1)
          begin
            #(`P);
            if (buffer_full !== 0) error; // should keep 0
          end

        // hash an empty string, should not eat next input
        reset = 1; #(`P); reset = 0;
        #(7*`P); // wait some cycles
        in = 32'h12345678; // should not be eat
        byte_num = 0;
        in_ready = 1;
        is_last = 1;
        #(`P);
        in = 32'hddddd; // should not be eat
        in_ready = 1; // next input
        is_last = 1;
        #(`P);
        in_ready = 0;
        is_last = 0;

        while (out_ready !== 1)
            #(`P);
        check(512'h0eab42de4c3ceb9235fc91acffe746b29c29a8c366b7c60e4e67c466f36a4304c00fa9caf9d87976ba469bcbe06713b435f091ef2769fb160cdab33d3670680e);
        for(i=0; i<5; i=i+1)
          begin
            #(`P);
            if (buffer_full !== 0) error; // should keep 0
          end

        // hash an (576-8) bit string
        reset = 1; #(`P); reset = 0;
        #(4*`P); // wait some cycles
        in_ready = 1;
        byte_num = 3; /* should have no effect */
        is_last = 0;
        for (i=0; i<8; i=i+1)
          begin
            in = 32'hEFCDAB90; #(`P);
            in = 32'h78563412; #(`P);
          end
        in = 32'hEFCDAB90; #(`P);
        in = 32'h78563412; is_last = 1; #(`P);
        in_ready = 0;
        is_last = 0;
        while (out_ready !== 1)
            #(`P);
        check(512'hf7f6b44069dba8900b6711ffcbe40523d4bb718cc8ed7f0a0bd28a1b18ee9374359f0ca0c9c1e96fcfca29ee2f282b46d5045eff01f7a7549eaa6b652cbf6270);

        // pad an (576-64) bit string
        reset = 1; #(`P); reset = 0;
        // don't wait any cycle
        in_ready = 1;
        byte_num = 7; /* should have no effect */
        is_last = 0;
        for (i=0; i<8; i=i+1)
          begin
            in = 32'hEFCDAB90; #(`P);
            in = 32'h78563412; #(`P);
          end
        is_last = 1;
        byte_num = 0;
        #(`P);
        in_ready = 0;
        is_last = 0;
        in = 0;
        while (out_ready !== 1)
            #(`P);
        check(512'hccd91653872c106f6eea1b8b68a4c2901c8d9bed9c180201f8a6144e7e6e6c251afcb6f6da44780b2d9aabff254036664719425469671f7e21fb67e5280a27ed);

        // pad an (576*2-16) bit string
        reset = 1; #(`P); reset = 0;
        in_ready = 1;
        byte_num = 1; /* should have no effect */
        is_last = 0;
        for (i=0; i<9; i=i+1)
          begin
            in = 32'hEFCDAB90; #(`P);
            in = 32'h78563412; #(`P);
          end
        #(`P/2);
        if (buffer_full !== 1) error; // should not eat
        #(`P/2);
        in = 32'h999; // should not eat this
        in_ready = 0;
        #(`P/2);
        if (buffer_full !== 0) error; // should not eat, but buffer should not be full
        #(`P/2);
        #(`P);
        // feed next (576-16) bit
        in_ready = 1;
        for (i=0; i<8; i=i+1)
          begin
            in = 32'hEFCDAB90; #(`P);
            in = 32'h78563412; #(`P);
          end
        in = 32'hEFCDAB90; #(`P);
        byte_num = 2;
        is_last = 1;
        in = 32'h78563412;
        #(`P);
        is_last = 0;
        in_ready = 0;
        while (out_ready !== 1)
            #(`P);
        check(512'h0f385323604e279251e80f928cfd9ce9492ba5df775063ea106eebe2a2c7785a3e33b4397fca66e90f67470334c66ea12016cb1f06170b9b033f158a7c01933e);

        $display("Good!");
        $finish;
    end

    always #(`P/2) clk = ~ clk;
    always #(`P*2) instrumented_clk = ~ instrumented_clk;

    task error;
        begin
              $display("E");
              $finish;
        end
    endtask

    task check;
        input [511:0] wish;
        begin
          if (out !== wish)
            begin
              $display("%h %h", out, wish); error;
            end
        end
    endtask
endmodule

`undef P
