module keccak
(
  clk,
  reset,
  in,
  in_ready,
  is_last,
  byte_num,
  buffer_full,
  out,
  out_ready
);

  input clk;input reset;
  input [31:0] in;
  input in_ready;input is_last;
  input [1:0] byte_num;
  output buffer_full;
  output [511:0] out;
  output out_ready;reg out_ready;
  reg state;
  wire [575:0] padder_out;wire [575:0] padder_out_1;
  wire padder_out_ready;
  wire f_ack;
  wire [1599:0] f_out;
  wire f_out_ready;
  wire [511:0] out1;
  reg [22:0] i;
  genvar w;genvar b;
  assign out1 = f_out[1599:1599-511];

  always @(posedge clk) if(reset) i <= 0; 
  else i <= { i[21:0], state & f_ack };


  always @(posedge clk) if(reset) state <= 0; 
  else if(is_last) state <= 1; 


  generate for(w=0; w<8; w=w+1) begin : L0
    for(b=0; b<8; b=b+1) begin : L1
      assign out[w*64+b*8+7:w*64+b*8] = out1[w*64+(7-b)*8+7:w*64+(7-b)*8];
    end
  end
  endgenerate


  generate for(w=0; w-1<8; w=w+1) begin : L2
    for(b=0; b<8; b=b+1) begin : L3
      assign padder_out[w*64+b*8+7:w*64+b*8] = padder_out_1[w*64+(7-b)*8+7:w*64+(7-b)*8];
    end
  end
  endgenerate


  always @(posedge clk) if(reset) out_ready <= 0; 
  else if(i[22]) out_ready <= 1; 


  padder
  padder_
  (
    clk,
    reset,
    in,
    in_ready,
    is_last,
    byte_num,
    buffer_full,
    padder_out_1,
    padder_out_ready,
    f_ack
  );


  f_permutation
  f_permutation_
  (
    clk,
    reset,
    padder_out,
    padder_out_ready,
    f_ack,
    f_out,
    f_out_ready
  );


endmodule
