module tb;
  reg clk;
  reg rstn;
  reg t;
 
  tff u0 (  .clk(clk),
            .rstn(rstn),
            .t(t),
          .q(q));
 
  always #5 clk = ~clk;
 
  initial begin  
    {rstn, clk, t} <= 0;
 
    $monitor ("T=%0t rstn=%0b t=%0d q=%0d", $time, rstn, t, q);
    repeat(2) @(posedge clk);
    rstn <= 1;
 
    for (integer i = 0; i < 20; i = i+1) begin
      reg [4:0] dly = $random;
      #(dly) t <= $random;
    end
  #20 $finish;
  end
endmodule