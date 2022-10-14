module first_counter
(
  clk,
  reset,
  enable,
  counter_out,
  overflow_out
);

  input clk;
  input reset;
  input enable;
  output [3:0] counter_out;
  output overflow_out;
  wire clk;
  wire reset;
  wire enable;
  reg [3:0] counter_out;
  reg overflow_out;

  always @(posedge clk) begin : COUNTER
    if(reset == 1'b1) begin
      counter_out <= #1 4'b0000;
      overflow_out <= #1 1'b0;
    end else if(enable == 1'b1) begin
      counter_out <= #1 counter_out + 1;
      if(counter_out == 4'b1111) begin
        overflow_out <= #1 1'b1;
      end 
    end else if(counter_out == 4'b1111) begin
      overflow_out <= #1 1'b1;
    end 
  end


endmodule
