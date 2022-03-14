//`include "fsm_full.v"

module fsm_full_tb();
reg clock , reset ;
reg req_0 , req_1 ,  req_2 , req_3; 
wire gnt_0 , gnt_1 , gnt_2 , gnt_3 ;

integer f;

initial begin
  f = $fopen("output.txt");
  $fwrite(f, "Time\t    R0 R1 R2 R3 G0 G1 G2 G3\n");
  $fmonitor(f, "%g\t    %b  %b  %b  %b  %b  %b  %b  %b", 
    $time, req_0, req_1, req_2, req_3, gnt_0, gnt_1, gnt_2, gnt_3);
  clock = 0;
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
