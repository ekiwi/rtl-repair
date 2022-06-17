module test(input in, output out);

// needs `rand const` for yosys to treat it as a synthesis constant
reg __synth_change_1;

assign out = __synth_change_1? !in : in;

endmodule


// pyverilog output
// Source:  (at 1)
//   Description:  (at 1)
//     ModuleDef: test (at 1)
//       Paramlist:  (at 0)
//       Portlist:  (at 1)
//         Ioport:  (at 1)
//           Input: in, False (at 1)
//         Ioport:  (at 1)
//           Output: out, False (at 1)
//       Decl:  (at 4)
//         Reg: __synth_change_1, False (at 4)
//       Assign:  (at 6)
//         Lvalue:  (at 6)
//           Identifier: out (at 6)
//         Rvalue:  (at 6)
//           Cond:  (at 6)
//             Identifier: __synth_change_1 (at 6)
//             Ulnot:  (at 6)
//               Identifier: in (at 6)
//             Identifier: in (at 6)
            
