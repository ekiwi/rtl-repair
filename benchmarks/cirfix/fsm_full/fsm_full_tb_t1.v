//`include "fsm_full.v"

module fsm_full_tb();
reg clock , reset ;
reg instrument_clock;
reg req_0 , req_1 ,  req_2 , req_3; 
wire gnt_0 , gnt_1 , gnt_2 , gnt_3 ;

integer f;

initial begin
  f = $fopen("output_fsm_full_tb_t1.txt");
  $display("time\t    req_0 req_1 req_2 req_3 gnt_0 gnt_1 gnt_2 gnt_3");
  $fwrite(f, "time,gnt_0,gnt_1,gnt_2,gnt_3\n");
  $monitor("%g\t    %b  %b  %b  %b  %b  %b  %b  %b", 
    $time, req_0, req_1, req_2, req_3, gnt_0, gnt_1, gnt_2, gnt_3);
  forever begin
    @(posedge clock);
    $fwrite(f, "%g,%b,%b,%b,%b\n", 
     $time, gnt_0, gnt_1, gnt_2, gnt_3);
  end
end

initial begin
  #4
  clock = 0;
  instrument_clock = 0;
  reset = 0;
  req_0 = 0;
  req_1 = 0;
  req_2 = 0;
  req_3 = 0;
  #10 reset = 1;
  #10 reset = 0;
  #10 req_0 = 1;
  #20 req_0 = 0;
  #10 req_1 = 1;
  #20 req_1 = 0;
  #10 req_2 = 1;
  #20 req_2 = 0;
  #10 req_3 = 1;
  #20 req_3 = 0;
  #10
  $fclose(f);
  $finish;
end

always
 #2 clock = ~clock;

always
  #8 instrument_clock = ~instrument_clock;

fsm_full U_fsm_full(
clock , // Clock
reset , // Active high reset
req_0 , // Active high request from agent 0
req_1 , // Active high request from agent 1
req_2 , // Active high request from agent 2
req_3 , // Active high request from agent 3
gnt_0 , // Active high grant to agent 0
gnt_1 , // Active high grant to agent 1
gnt_2 , // Active high grant to agent 2
gnt_3   // Active high grant to agent 3
);



endmodule
