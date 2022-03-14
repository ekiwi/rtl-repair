module tb;
  reg clk;
  reg instrumented_clk;
  reg rstn;
  reg t;

  tff u0 (  .clk(clk),
            .rstn(rstn),
            .t(t),
          .q(q));

  always #5 clk = ~clk;
  always #20 instrumented_clk = ~instrumented_clk;

  integer f;

  initial begin
    f = $fopen("output_tff_tb.txt");
    $fwrite(f, "time,rstn,t,q\n");
    forever begin
        @(posedge clk);
        $fwrite(f, "%g,%b,%b,%b\n", $time,rstn,t,q);
    end

  end

  initial begin
    {rstn, clk, t, instrumented_clk} <= 0;
    $monitor ("T=%0t rstn=%0b t=%0d q=%0d", $time, rstn, t, q);
    repeat(2) @(posedge clk);
    rstn <= 1;

    for (integer i = 0; i < 20; i = i+1) begin
      reg [4:0] dly = $random;
      #(dly) t <= $random;
    end
  // #20 $fclose(f);
  #20 $finish;
  end
endmodule
