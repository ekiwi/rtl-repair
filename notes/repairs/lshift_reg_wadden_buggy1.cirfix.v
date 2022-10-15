module lshift_reg
(
  input clk,
  input rstn,
  input [7:0] load_val,
  input load_en,
  output reg [7:0] op
);

  integer i;

  always @(posedge clk) begin
    if(!rstn) begin
      op = 0;
    end else begin
      if(load_en) begin
        op = load_val;
      end else begin
        for(i=0; i<8; i=i+1) begin
          op[i + 1] <= op[i];
        end
        op[0] = op[7];
      end
    end
  end


endmodule
