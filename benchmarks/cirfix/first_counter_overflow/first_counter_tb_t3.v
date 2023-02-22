// Self-checking testbench for first_counter.v
// DUT is instantiated in tb, tb will contain a clock generator, reset
// generator, enable logic generator, compare logic.


// step1: create a dummy template that declares inputs to DUT as reg,
// declare outputs of DUT as wire. Note there is no port list for test
// bench.
module first_counter_tb;
reg clk, reset, enable;
reg instrument_clk;
wire[3:0] counter_out;
wire overflow_out;


first_counter U0(
    .clk (clk),
    .reset (reset),
    .enable (enable),
    .counter_out (counter_out),
    .overflow_out (overflow_out)
);

// step2: add clock generator logic. Before this we need to drive all
// inputs of DUT to some known state.
initial begin // initial block only executes once 
    clk = 0;
    instrument_clk = 0;
    reset = 0;
    enable = 0;
end

always
    #5 clk = !clk;

always
    #5 instrument_clk = !instrument_clk; // IMPORTANT: Make sure that this reflects the granularity of the oracle w.r.t. the clock cycle!


integer f;
initial begin
    f = $fopen("output_first_counter_tb_t3.txt");
    $display("\t\ttime,\tclk,\treset,\tenable,\tcount_out,\toverflow_out\n");
    $fwrite(f, "time,counter_out[3],counter_out[2],counter_out[1],counter_out[0],overflow_out\n");
    $monitor("%d, \t%b, \t%b, \t%b, \t%d, \t\t%b", $time, clk, reset, enable, counter_out, overflow_out);
    forever begin
    @(posedge instrument_clk);
    $fwrite(f, "%g,%b,%b,%b,%b,%b\n", $time, counter_out[3], counter_out[2], counter_out[1], counter_out[0], overflow_out);
    end
end



event reset_trigger;
event reset_done_trigger;
event terminate_sim;


initial begin
    #5
    forever begin
        @(reset_trigger);
        @(negedge clk);
        reset = 1;
        @(negedge clk);
        reset = 0;
        -> reset_done_trigger;
    end
end

initial begin
    @(terminate_sim);
    #5
    $fclose(f);
    $finish;
end

/*
// Test Case 1: Assert/Deassert reset
// trigger the reset_trigger event after 10 time units
initial begin: TEST_CASE_1
    #10 -> reset_trigger;
end
*/



// Test Case 2: Assert/Deassert enable after reset is applied
// trigger the reset logic and wait for it to complete. Then drive
// enable to 1
/*
reg temp_event1;

initial begin
    temp_event1 = 0;
       #10;
    temp_event1 = 1;
end
*/
/*
initial begin: TEST_CASE_2
    #10 -> reset_trigger;
   // @(posedge temp_event1);
    
    @(reset_done_trigger);
    @(negedge clk);
    enable = 1;
    repeat (10) begin
        @(negedge clk);
    end
    enable = 0;
    #5 -> terminate_sim;
end
*/

initial begin: TEST_CASE_4
    #10 -> reset_trigger;
   // @(posedge temp_event1);
    
    @(reset_done_trigger);
    @(negedge clk);
    enable = 1;
    repeat (100) begin
        @(negedge clk);
    end
    enable = 0;
    #5 -> terminate_sim;
end

initial begin
    #253
    
    //@(negedge clk)
    //#5 $display ("Simulation SUCCESS!");
     -> terminate_sim; // terminate simulation after 100 time units.

end

endmodule
