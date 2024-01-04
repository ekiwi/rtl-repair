
// Language: Verilog 2001

`timescale 1ns / 1ps

/*
 * Testbench for axis_frame_len
 */
module test_axis_frame_len_8();


reg genclock;
reg clk;

initial begin
    clk = 0;
    forever begin
        #1 clk = ~clk; 
    end
end

// Parameters
parameter DATA_WIDTH = 8;
parameter KEEP_ENABLE = (DATA_WIDTH>8);
parameter KEEP_WIDTH = (DATA_WIDTH/8);
parameter LEN_WIDTH = 16;

// Inputs

reg rst = 1;
reg [7:0] current_test = 0;

reg [KEEP_WIDTH-1:0] monitor_axis_tkeep = 0;
reg monitor_axis_tvalid = 0;
reg monitor_axis_tready = 0;
reg monitor_axis_tlast = 0;

reg [31:0] cycle = 0;

// Outputs
wire [LEN_WIDTH-1:0] frame_len;
wire frame_len_valid;


integer f;
// dump I/O
initial begin
  f = $fopen("output.txt");
  $fwrite(f, "rst, monitor_axis_tkeep, monitor_axis_tvalid, monitor_axis_tready, monitor_axis_tlast, frame_len, frame_len_valid\n");
  forever begin
    @(posedge clk);
    $fwrite(f, "%d,%d,%d,%d,%d,%d,%d\n", rst, monitor_axis_tkeep, monitor_axis_tvalid, monitor_axis_tready, monitor_axis_tlast, frame_len, frame_len_valid);
  end
end

initial begin

    // myhdl integration
    
    rst = 1'b1;
    monitor_axis_tkeep = 0;
    monitor_axis_tvalid = 0;
    monitor_axis_tready = 0;
    monitor_axis_tlast = 0;
    
    
end

always @(posedge clk) begin
        genclock <= cycle < 6;
        cycle <= cycle + 1;

        if(cycle == 0) begin
            rst <= 1'b0;
            monitor_axis_tkeep <= 0;
            monitor_axis_tvalid <= 1'b1;
            monitor_axis_tready <= 0;
            monitor_axis_tlast <= 0;
        end
        else if (cycle == 1) begin
            rst <= 1'b0;
            monitor_axis_tkeep <= 1'b1;
            monitor_axis_tvalid <= 1'b1;
            monitor_axis_tready <= 1'b1;
            monitor_axis_tlast <= 0;
        end
        else if(cycle == 2) begin
            rst <= 1'b0;
            monitor_axis_tkeep <= 1'b1;
            monitor_axis_tvalid <= 1'b1;
            monitor_axis_tready <= 1'b1;
            monitor_axis_tlast <= 1'b1;
        end
        else if(cycle == 3) begin
            rst <= 1'b0;
            monitor_axis_tkeep <= 1'b1;
            monitor_axis_tvalid <= 1'b1;
            monitor_axis_tready <= 1'b1;
            monitor_axis_tlast <= 1'b1;
        end
        else if(cycle == 4) begin
            rst <= 1'b0;
            monitor_axis_tkeep <= 1'b0;
            monitor_axis_tvalid <= 1'b0;
            monitor_axis_tready <= 1'b1;
            monitor_axis_tlast <= 1'b0;
        end
        else if(cycle == 5) begin
            rst <= 1'b0;
            monitor_axis_tkeep <= 1'b0;
            monitor_axis_tvalid <= 1'b0;
            monitor_axis_tready <= 1'b1;
            monitor_axis_tlast <= 1'b0;
            if (frame_len>1) begin
                $display("@@@Error: The frame_len is incorrrect.");
            end
            $finish;
        end
    end

axis_frame_len 
UUT (
    .clk(clk),
    .rst(rst),
    // AXI monitor
    .monitor_axis_tkeep(monitor_axis_tkeep),
    .monitor_axis_tvalid(monitor_axis_tvalid),
    .monitor_axis_tready(monitor_axis_tready),
    .monitor_axis_tlast(monitor_axis_tlast),
    // Status
    .frame_len(frame_len),
    .frame_len_valid(frame_len_valid)
);


`ifdef DUMP_TRACE // used for our OSDD calculations
initial begin
  $dumpfile("dump.vcd");
  $dumpvars(0, UUT);
end
`endif // DUMP_TRACE

endmodule
