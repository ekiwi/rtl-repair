module sync_ff(input clock, input reset, input in, output out);

reg r;

always @(posedge clock)
  if (reset) r <= 1'b0;
  else r <= in;

assign out = r;

endmodule