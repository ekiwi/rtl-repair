`timescale 1ns / 100ps
/**********************************************************************
 * Date: Aug. 28, 1999
 * File: Test Decoder 3 to 8.v   (440 Examples)
 *
 * Testbench to generate some stimulus and display the results for the
 * 3-to-8 decoder module.
 **********************************************************************/
//*********************************************************
  module Test_decoder_3to8;
//*********************************************************  
     wire  Y7, Y6, Y5, Y4, Y3, Y2, Y1, Y0;
     reg   A, B, C;
     reg   en;
     reg   clk, instrumented_clk;
     // Instantiate the Decoder (named DUT {device under test})
     decoder_3to8  DUT(Y7,Y6,Y5,Y4,Y3,Y2,Y1,Y0, A, B, C, en);
  

`ifdef DUMP_TRACE // used for our OSDD calculations
      initial begin
        $dumpfile("dump.vcd");
        $dumpvars(0, DUT);
      end
`endif // DUMP_TRACE

     integer f;
     initial  begin
        clk = 0;
        instrumented_clk = 0;
        A  = 1'b0;       // time = 0
        B  = 1'b0;
        C  = 1'b0;
        en = 1'b0;
        f = $fopen("output_decoder_3_to_8_tb_t1.txt");
        $fwrite(f, "time,Y7,Y6,Y5,Y4,Y3,Y2,Y1,Y0\n");
        $timeformat(-9, 1, " ns", 6); #1;
        #9;
        en = 1'b1;      // time = 10
        #10;
        A  = 1'b0;
        B  = 1'b1; 
        C  = 1'b0;      // time = 20
        #10;
        A  = 1'b1;
        B  = 1'b0;      
        C  = 1'b0;      // time = 30
        #10;
        A  = 1'b1;
        B  = 1'b1;
        C  = 1'b0;      // time = 40
        #5;
        en = 1'b0;      // time = 45
        #10;
        $fclose(f);
	$finish;
     end
 
    //  always @(A or B or C or en)
    always @(posedge clk)
     $fwrite(f, "%g,%b,%b,%b,%b,%b,%b,%b,%b\n", $time,Y7,Y6,Y5,Y4,Y3,Y2,Y1,Y0);

     always @(A or B or C or en)  
     $monitor("t=%t en=%b ABC=%b%b%b Y=%b%b%b%b%b%b%b%b",
$time,en,A,B,C,Y7,Y6,Y5,Y4,Y3,Y2,Y1,Y0);

    always #1 clk = ~clk;
    always #1 instrumented_clk = ~instrumented_clk;
    
  endmodule
