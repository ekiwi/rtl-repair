// Self-checking testbench for first_counter.v
// DUT is instantiated in tb, tb will contain a clock generator, reset
// generator, enable logic generator, compare logic.


// step1: create a dummy template that declares inputs to DUT as reg,
// declare outputs of DUT as wire. Note there is no port list for test
// bench.
module first_counter_tb;
reg clk, reset, enable;
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
    reset = 0;
    enable = 0;
end

always
    #5 clk = !clk;

/*
initial begin
    $dumpfile ("first_counter.vcd"); //dumpfile is for specifying the file that simulator will use to store the waveform
    $dumpvars; // dumpvars instructs the Verilog compiler to start dumping all signals to the dumpfile.
end
*/

integer f;
initial begin
    f = $fopen("output.txt");
    $fwrite(f, "\t\ttime,\tclk,\treset,\tenable,\tcount_out,\toverflow_out\n");
    $fmonitor(f,"%d, \t%b, \t%b, \t%b, \t%d, \t\t%b", $time, clk, reset, enable, counter_out, overflow_out);

end



event reset_trigger;
event reset_done_trigger;
event terminate_sim;


initial begin
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


/*
// Test Case 3: Assert/Deassert enable and reset randomly
initial begin: TEST_CASE_3
    #10 -> reset_trigger
    @(reset_done_trigger);
    fork
        repeat (10) begin
            @(negedge clk);
            enable = $random
        end
        repeat (10) begin
            @(negedge clk);
            reset = $random;
        end
    join
end
*/

// Adding Compare logic
reg [3:0] count_compare;
//reg overflow_compare;

always @ (posedge clk)
    if (reset==1'b1) begin
        count_compare<=0;
        //overflow_compare<=0;
    end 
    else if (enable == 1'b1) begin
        count_compare <= count_compare + 1;
    end
    //if (count_compare ==4'b1111) begin
    //    overflow_compare <= 1;
    //end


// Adding checking logic: at any given point, keep checking the expected
// value with the actual value. Whenever there is an error, print out
// the expected and actual value, also terminate the simulation by
// trigering the event "terminate_sim".
always@(posedge clk)
    if (count_compare != counter_out) begin
        $display ("DUT ERROR at time %d", $time);
        $display ("Expected Value %d, Got Value %d", count_compare, counter_out);
        #5 -> terminate_sim;
    end
    //if (overflow_compare != overflow_out) begin
    //    $display ("DUT ERROR at time %d", $time);
    //    $display ("Expected Value %d, Got Value %d", overflow_compare, overflow_out);
    //end


initial begin
    #250
    
    //@(negedge clk)
    //#5 $display ("Simulation SUCCESS!");
     -> terminate_sim; // terminate simulation after 100 time units.

end

endmodule
