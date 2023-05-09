

module mux_4to1_case
(
  input [3:0] a,
  input [3:0] b,
  input [3:0] c,
  input [3:0] d,
  input [1:0] sel,
  output reg [3:0] out
);


  always @(a or b or c or d or sel) begin
    case(sel)
      2'b00: out <= a;
      2'b01: out <= b;
      2'b10: out <= c;
      2'b11: out <= d;
    endcase
  end


endmodule

