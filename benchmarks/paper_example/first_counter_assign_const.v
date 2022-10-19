module first_counter(
    input clock,
    input reset,
    input enable,
    output reg [3:0] count,
    output reg overflow,
   input phi0, input [3:0] alpha0,
   input phi1, input [3:0] alpha1
);
always@(posedge clock) begin
 if(reset == 1'b1) begin
   overflow <= 1'b0;
   if(phi0) count <= alpha0;
 end else if(enable == 1'b1) begin
   count <= count + 1;
 end
 if(count == 4'b1111) begin
   overflow <= 1'b1;
   if(phi1) count <= alpha1;
 end
end
endmodule
