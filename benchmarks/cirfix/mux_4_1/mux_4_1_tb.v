module tb_4to1_mux;

   reg [3:0] a;
   reg [3:0] b;
   reg [3:0] c;
   reg [3:0] d;
   wire [3:0] out;
   reg [1:0] sel;

   reg clk;
   reg instrumented_clk;

   integer i;
   
   always #5 clk = !clk;
   always #20 instrumented_clk = !instrumented_clk;

   mux_4to1_case  mux0 (   .a (a),
                           .b (b),
                           .c (c),
                           .d (d),
                           .sel (sel),
                           .out (out));


   integer f;

   initial begin
       f = $fopen("output_mux_4_1_tb.txt");
       $fwrite(f, "time,out[3],out[2],out[1],out[0]\n");
       forever begin
           @(posedge clk);
           $fwrite(f, "%g,%b,%b,%b,%b\n", $time,out[3],out[2],out[1],out[0]);
       end
   end
   initial begin
      $monitor ("[%0t] sel=0x%0h a=0x%0h b=0x%0h c=0x%0h d=0x%0h out=0x%0h", $time, sel, a, b, c, d, out);

   	clk = 0;
      instrumented_clk = 0;

      sel <= 2'b00;
      a <= 4'b0001;
      b <= 4'b0010;
      c <= 4'b0100;
      d <= 4'b1000;

      #100;
      sel <= 2'b01;
      #100;
      sel <= 2'b10;
      #100;
      sel <= 2'b11;
      
      #100;

      sel <= 2'b00;
      d <= 4'b0001;
      c <= 4'b0010;
      b <= 4'b0100;
      a <= 4'b1000;

      #100;
      sel <= 2'b01;
      #100;
      sel <= 2'b10;
      #100;
      sel <= 2'b11;


      #800 $finish;
      #850 $fclose(f);
   end

endmodule