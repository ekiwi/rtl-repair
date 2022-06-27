// yosys read_verilog:
// >> Warning: Yosys has only limited support for tri-state logic at the moment. (test.sv:5)
// the btor and smt produced by yosys are both not very helpful :(
//
// according to this question on reddit, there might be a command to emulate tristate logic:
// https://www.reddit.com/r/yosys/comments/60yqrq/limited_support_for_tristate_logic/
//
module test(input read, inout io, output out);

assign out = io;
// tri state buffer
assign io  = (read) ? 1'bz : 1'b1;

endmodule