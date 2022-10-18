module first_counter(
    input clock,
    input reset,
    input enable,
    output reg [3:0] counter_out,
    output reg overflow_out
);
always@(posedge clock) begin
    if(reset == 1'b1) begin
        overflow_out <= 1'b0;
    end else if(enable == 1'b1) begin
        counter_out <= counter_out + 1;
    end
    if(counter_out == 4'b1111) begin
        overflow_out <= 1'b1;
    end
end
endmodule
