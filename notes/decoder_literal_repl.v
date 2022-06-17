// this was produced by our prototype literal replacer written in python

module decoder_3to8
(
  Y7,
  Y6,
  Y5,
  Y4,
  Y3,
  Y2,
  Y1,
  Y0,
  A,
  B,
  C,
  en
);

  reg __synth_change_literal_0;assign __synth_change_literal_0 = $anyconst;
  reg __synth_change_literal_1;assign __synth_change_literal_1 = $anyconst;
  reg __synth_change_literal_2;assign __synth_change_literal_2 = $anyconst;
  reg __synth_change_literal_3;assign __synth_change_literal_3 = $anyconst;
  reg __synth_change_literal_4;assign __synth_change_literal_4 = $anyconst;
  reg __synth_change_literal_5;assign __synth_change_literal_5 = $anyconst;
  reg __synth_change_literal_6;assign __synth_change_literal_6 = $anyconst;
  reg __synth_change_literal_7;assign __synth_change_literal_7 = $anyconst;
  reg __synth_change_literal_8;assign __synth_change_literal_8 = $anyconst;
  reg __synth_change_literal_9;assign __synth_change_literal_9 = $anyconst;
  reg __synth_change_literal_10;assign __synth_change_literal_10 = $anyconst;
  reg __synth_change_literal_11;assign __synth_change_literal_11 = $anyconst;
  reg __synth_change_literal_12;assign __synth_change_literal_12 = $anyconst;
  reg __synth_change_literal_13;assign __synth_change_literal_13 = $anyconst;
  reg __synth_change_literal_14;assign __synth_change_literal_14 = $anyconst;
  reg __synth_change_literal_15;assign __synth_change_literal_15 = $anyconst;
  reg __synth_change_literal_16;assign __synth_change_literal_16 = $anyconst;
  reg [3:0] __synth_literal_0;assign __synth_literal_0 = $anyconst;
  reg [3:0] __synth_literal_1;assign __synth_literal_1 = $anyconst;
  reg [3:0] __synth_literal_2;assign __synth_literal_2 = $anyconst;
  reg [3:0] __synth_literal_3;assign __synth_literal_3 = $anyconst;
  reg [3:0] __synth_literal_4;assign __synth_literal_4 = $anyconst;
  reg [3:0] __synth_literal_5;assign __synth_literal_5 = $anyconst;
  reg [3:0] __synth_literal_6;assign __synth_literal_6 = $anyconst;
  reg [3:0] __synth_literal_7;assign __synth_literal_7 = $anyconst;
  reg [7:0] __synth_literal_8;assign __synth_literal_8 = $anyconst;
  reg [7:0] __synth_literal_9;assign __synth_literal_9 = $anyconst;
  reg [7:0] __synth_literal_10;assign __synth_literal_10 = $anyconst;
  reg [7:0] __synth_literal_11;assign __synth_literal_11 = $anyconst;
  reg [7:0] __synth_literal_12;assign __synth_literal_12 = $anyconst;
  reg [7:0] __synth_literal_13;assign __synth_literal_13 = $anyconst;
  reg [7:0] __synth_literal_14;assign __synth_literal_14 = $anyconst;
  reg [7:0] __synth_literal_15;assign __synth_literal_15 = $anyconst;
  reg [7:0] __synth_literal_16;assign __synth_literal_16 = $anyconst;
  output Y7;output Y6;output Y5;output Y4;output Y3;output Y2;output Y1;output Y0;
  input A;input B;input C;
  input en;
  assign { Y7, Y6, Y5, Y4, Y3, Y2, Y1, Y0 } = ({ en, A, B, C } == ((__synth_change_literal_0)? __synth_literal_0 : 4'b1000))? (__synth_change_literal_16)? __synth_literal_16 : 8'b1111_1110 : 
                                              ({ en, A, B, C } == ((__synth_change_literal_1)? __synth_literal_1 : 4'b1001))? (__synth_change_literal_15)? __synth_literal_15 : 8'b1111_1101 : 
                                              ({ en, A, B, C } == ((__synth_change_literal_2)? __synth_literal_2 : 4'b1000))? (__synth_change_literal_14)? __synth_literal_14 : 8'b1111_1011 : 
                                              ({ en, A, B, C } == ((__synth_change_literal_3)? __synth_literal_3 : 4'b1011))? (__synth_change_literal_13)? __synth_literal_13 : 8'b1111_0111 : 
                                              ({ en, A, B, C } == ((__synth_change_literal_4)? __synth_literal_4 : 4'b1100))? (__synth_change_literal_12)? __synth_literal_12 : 8'b1110_1111 : 
                                              ({ en, A, B, C } == ((__synth_change_literal_5)? __synth_literal_5 : 4'b1101))? (__synth_change_literal_11)? __synth_literal_11 : 8'b1101_1111 : 
                                              ({ en, A, B, C } == ((__synth_change_literal_6)? __synth_literal_6 : 4'b1110))? (__synth_change_literal_10)? __synth_literal_10 : 8'b1011_1111 : 
                                              ({ en, A, B, C } == ((__synth_change_literal_7)? __synth_literal_7 : 4'b1111))? (__synth_change_literal_9)? __synth_literal_9 : 8'b0111_1111 : 
                                              (__synth_change_literal_8)? __synth_literal_8 : 8'b0111_1111;

endmodule
