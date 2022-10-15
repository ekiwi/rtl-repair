module padder
(
  clk,
  reset,
  in,
  in_ready,
  is_last,
  byte_num,
  buffer_full,
  out,
  out_ready,
  f_ack
);

  input clk;input reset;
  input [31:0] in;
  input in_ready;input is_last;
  input [1:0] byte_num;
  output buffer_full;
  output [575:0] out;reg [575:0] out;
  output out_ready;
  input f_ack;
  reg state;
  reg done;
  reg [17:0] i;
  wire [31:0] v0;
  reg [31:0] v1;
  wire accept;wire update;
  assign buffer_full = i[17];
  assign out_ready = buffer_full;
  assign accept = ~state & in_ready & ~buffer_full;
  assign update = (accept | state) & ~done;

  always @(posedge clk) if(reset) out <= 0; 
  else if(update) out <= { out[575-32:0], v1 }; 


  always @(posedge clk) if(reset) i <= 0; 
  else if(f_ack | update) i <= { i[16:0], 1'b1 } & { 18{ ~f_ack } }; 


  always @(posedge clk) if(reset) state <= 0; 
  else if(is_last) state <= 1; 


  always @(*) if(reset) done <= 0; 
  else if(state & out_ready) done <= 1; 


  padder1
  p0
  (
    in,
    byte_num,
    v0
  );


  always @(*) begin
    if(state) begin
      v1 = 0;
      v1[7] = v1[7] | i[16];
    end else if(is_last == 0) v1 = in; 
    else begin
      v1 = v0;
      v1[7] = v1[7] | i[16];
    end
  end


endmodule
