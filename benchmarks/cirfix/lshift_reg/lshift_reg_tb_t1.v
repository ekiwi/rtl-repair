module tb;
  reg clk;
  reg instrumented_clk;
  reg rstn;
  reg [7:0] load_val;
  reg load_en;
  wire [7:0] op;
 
  // Setup DUT clock
  always #10 clk = ~clk;
  always #40 instrumented_clk = ~instrumented_clk;
 
  // Instantiate the design
  lshift_reg u0 ( .clk(clk),
                 .rstn (rstn),
                 .load_val (load_val),
                 .load_en (load_en),
                 .op (op));

  integer f;
  initial begin
    f = $fopen("output_lshift_reg_tb_t1.txt");
    $fwrite(f,"time,op[7],op[6],op[5],op[4],op[3],op[2],op[1],op[0]\n");
    $monitor("%g, \t%b, \t%b, \t%b, \t%d, \t\t%b", $time, clk, rstn, load_val, load_en, op);
    forever begin
      @(posedge clk);
      $fwrite(f,"%g,%b,%b,%b,%b,%b,%b,%b,%b\n",$time,op[7],op[6],op[5],op[4],op[3],op[2],op[1],op[0]);
    end
  end
 
  initial begin
    // 1. Initialize testbench variables
    clk <= 0;
    instrumented_clk <= 0;
    rstn <= 0;
    load_val <= 8'h01;
    load_en <= 0;
 
    // 2. Apply reset to the design
    repeat (2) @ (posedge clk);
    rstn <= 1;
    repeat (5) @ (posedge clk);
 
    // 3. Set load_en for 1 clk so that load_val is loaded
    load_en <= 1;
    repeat(1) @ (posedge clk);
    load_en <= 0;
 
    // 4. Let design run for 20 clocks and then finish
    repeat (20) @ (posedge clk);
    $finish;
  end
endmodule
