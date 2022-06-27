// yosys read_verilog:
// >> Warning: Yosys has only limited support for tri-state logic at the moment. (test.sv:5)
// the btor and smt produced by yosys are both not very helpful :(
module test(input read, inout io, output out);

assign out = io;
// tri state buffer
assign io  = (read) ? 1'bz : 1'b1;

endmodule