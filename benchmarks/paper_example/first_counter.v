module first_counter(
    input clock,
    input reset,
    input enable,
    output reg [3:0] count,
    output reg overflow
);
always@(posedge clock) begin
  if(reset == 1'b1) begin
    overflow <= 1'b0;
  end else if(enable == 1'b1) begin
    count <= count + 1;
  end
  if(count == 4'b1111) begin
    overflow <= 1'b1; // comment
  end
end
endmodule
