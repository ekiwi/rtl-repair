`timescale 1ns / 100ps

/* This is a Verilog implementation of the "complete_min_tb.csv".
   Note that this test is only complete in a sense that it covers
   all execution paths in the design. It _does not_ cover all
   possible input combinations!
**/

module Test_decoder_3to8;
wire  Y7, Y6, Y5, Y4, Y3, Y2, Y1, Y0;
reg   A, B, C;
reg   en;
reg   clk;
decoder_3to8  DUT(Y7,Y6,Y5,Y4,Y3,Y2,Y1,Y0, A, B, C, en);
  

`ifdef DUMP_TRACE // used for our OSDD calculations
initial begin
  $dumpfile("dump.vcd");
  $dumpvars(0, DUT);
end
`endif // DUMP_TRACE

initial  begin
  clk = 0;
  @(posedge clk); A  = 1'b0; B  = 1'b0; C  = 1'b0; en = 1'b0;
  @(posedge clk); A  = 1'b0; B  = 1'b0; C  = 1'b1; en = 1'b1;
  @(posedge clk); A  = 1'b0; B  = 1'b1; C  = 1'b0; en = 1'b1;
  @(posedge clk); A  = 1'b0; B  = 1'b1; C  = 1'b1; en = 1'b1;
  @(posedge clk); A  = 1'b1; B  = 1'b0; C  = 1'b0; en = 1'b1;
  @(posedge clk); A  = 1'b1; B  = 1'b0; C  = 1'b1; en = 1'b1;
  @(posedge clk); A  = 1'b1; B  = 1'b1; C  = 1'b0; en = 1'b1;
  @(posedge clk); A  = 1'b1; B  = 1'b1; C  = 1'b1; en = 1'b1;
  @(posedge clk); A  = 1'b1; B  = 1'b0; C  = 1'b0; en = 1'b0;
  @(posedge clk); A  = 1'b1; B  = 1'b1; C  = 1'b0; en = 1'b0;
$finish;
end

integer f;
initial begin
  // compare to: oracle_complete.txt
  f = $fopen("output_decoder_3_to_8_tb_t1.txt");
  $fwrite(f, "time,Y7,Y6,Y5,Y4,Y3,Y2,Y1,Y0\n");
  $timeformat(-9, 1, " ns", 6);
    forever begin
    @(posedge clk);
    $fwrite(f, "%g,%b,%b,%b,%b,%b,%b,%b,%b\n", $time,Y7,Y6,Y5,Y4,Y3,Y2,Y1,Y0);
  end
end



always @(A or B or C or en)  
  $monitor("t=%t en=%b ABC=%b%b%b Y=%b%b%b%b%b%b%b%b",$time,en,A,B,C,Y7,Y6,Y5,Y4,Y3,Y2,Y1,Y0);

always #1 clk = ~clk;

endmodule
