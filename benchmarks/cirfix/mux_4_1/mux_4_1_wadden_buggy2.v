module mux_4to1_case ( input [3:0] a,                 // 4-bit input called a
                       input [3:0] b,                 // 4-bit input called b
                       input [3:0] c,                 // 4-bit input called c
                       input [3:0] d,                 // 4-bit input called d
                       input [1:0] sel,               // input sel used to select between a,b,c,d
                       output reg [3:0] out);         // 4-bit output based on input sel

   // This always block gets executed whenever a/b/c/d/sel changes value
   // When that happens, based on value in sel, output is assigned to either a/b/c/d
   always @ (a or b or c or d or sel) begin
      case (sel)
         2'h00 : out <= a;
         2'h01 : out <= b;
         2'h10 : out <= c;
         2'h11 : out <= d;
      endcase
   end
endmodule