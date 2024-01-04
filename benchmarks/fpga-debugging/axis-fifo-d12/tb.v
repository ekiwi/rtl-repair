/*

Copyright (c) 2014-2018 Alex Forencich

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

*/

// Language: Verilog 2001

`timescale 1ns / 1ps

/*
 * Testbench for axis_fifo
 */
module test_axis_fifo(input clk, output reg genclock);

// Parameters
parameter DEPTH = 4;
parameter DATA_WIDTH = 8;
parameter KEEP_ENABLE = (DATA_WIDTH>8);
parameter KEEP_WIDTH = (DATA_WIDTH/8);
parameter LAST_ENABLE = 1;
parameter ID_ENABLE = 1;
parameter ID_WIDTH = 8;
parameter DEST_ENABLE = 1;
parameter DEST_WIDTH = 8;
parameter USER_ENABLE = 1;
parameter USER_WIDTH = 1;
parameter FRAME_FIFO = 1;
parameter USER_BAD_FRAME_VALUE = 1'b1;
parameter USER_BAD_FRAME_MASK = 1'b1;
parameter DROP_BAD_FRAME = 0;
parameter DROP_WHEN_FULL = 1;

// derived
parameter ADDR_WIDTH = (KEEP_ENABLE && KEEP_WIDTH > 1) ? $clog2(DEPTH/KEEP_WIDTH) : $clog2(DEPTH);

// Inputs
reg [31:0] cycle = 0;

reg rst /*verilator public*/ = 0;
reg [7:0] current_test = 0;

reg [DATA_WIDTH-1:0] s_axis_tdata /*verilator public*/ = 0;
reg [KEEP_WIDTH-1:0] s_axis_tkeep /*verilator public*/ = 0;
reg s_axis_tvalid /*verilator public*/ = 0;
reg s_axis_tlast /*verilator public*/ = 0;
reg [ID_WIDTH-1:0] s_axis_tid /*verilator public*/ = 0;
reg [DEST_WIDTH-1:0] s_axis_tdest /*verilator public*/ = 0;
reg [USER_WIDTH-1:0] s_axis_tuser /*verilator public*/ = 0;
reg m_axis_tready /*verilator public*/ = 0;

// Outputs
wire s_axis_tready /*verilator public*/;
wire [DATA_WIDTH-1:0] m_axis_tdata /*verilator public*/;
wire [KEEP_WIDTH-1:0] m_axis_tkeep /*verilator public*/;
wire m_axis_tvalid /*verilator public*/;
wire m_axis_tlast /*verilator public*/;
wire [ID_WIDTH-1:0] m_axis_tid /*verilator public*/;
wire [DEST_WIDTH-1:0] m_axis_tdest /*verilator public*/;
wire [USER_WIDTH-1:0] m_axis_tuser /*verilator public*/;

initial begin
    // myhdl integration
    rst = 1'b1;
    s_axis_tdata = 1;
    s_axis_tkeep = 0;
    s_axis_tvalid = 1'b1;
    s_axis_tlast = 0;
    s_axis_tid = 1;
    s_axis_tdest = 0;
    s_axis_tuser = 0;
    m_axis_tready = 0;

end


always @(posedge clk) begin
    genclock <= cycle < 12;
    cycle <= cycle + 1;

    if(cycle == 0) begin
        rst <= 1'b0;
        s_axis_tdata <= 1;
        s_axis_tkeep <= 0;
        s_axis_tvalid <= 1'b1;
        s_axis_tlast <= 1;
        s_axis_tid <= 1;
        s_axis_tdest <= 0;
        s_axis_tuser <= 0;
        m_axis_tready <= 0;
        
    end
    else if (cycle == 1) begin
       s_axis_tdata <= 1;
        s_axis_tkeep <= 0;
        s_axis_tvalid <= 1'b1;
        s_axis_tlast <= 1;
        s_axis_tid <= 1;
        s_axis_tdest <= 0;
        s_axis_tuser <= 0;
        m_axis_tready <= 0;
    end
    else if(cycle == 2) begin
        s_axis_tdata <= 2;
        s_axis_tkeep <= 0;
        s_axis_tvalid <= 1'b1;
        s_axis_tlast <= 1;
        s_axis_tid <= 1;
        s_axis_tdest <= 0;
        s_axis_tuser <= 0;
        m_axis_tready <= 0;
    end
    else if(cycle == 3) begin
        s_axis_tdata <= 3;
        s_axis_tkeep <= 0;
        s_axis_tvalid <= 1'b1;
        s_axis_tlast <= 1;
        s_axis_tid <= 1;
        s_axis_tdest <= 0;
        s_axis_tuser <= 0;
        m_axis_tready <= 0;
    end
    else if(cycle == 4) begin
        s_axis_tdata <= 4;
        s_axis_tkeep <= 0;
        s_axis_tvalid <= 1'b1;
        s_axis_tlast <= 0;
        s_axis_tid <= 1;
        s_axis_tdest <= 0;
        s_axis_tuser <= 0;
        m_axis_tready <= 0;
    end
    else if (cycle == 5) begin
        s_axis_tdata <= 5;
        s_axis_tkeep <= 0;
        s_axis_tvalid <= 1'b1;
        s_axis_tlast <= 0;
        s_axis_tid <= 1;
        s_axis_tdest <= 0;
        s_axis_tuser <= 0;
        m_axis_tready <= 0;
    end
    else if (cycle == 6) begin
        s_axis_tdata <= 6;
        s_axis_tkeep <= 0;
        s_axis_tvalid <= 1'b1;
        s_axis_tlast <= 0;
        s_axis_tid <= 1;
        s_axis_tdest <= 0;
        s_axis_tuser <= 0;
        m_axis_tready <= 0;
    end
    else if(cycle == 7) begin
        m_axis_tready <= 1;
        s_axis_tvalid <= 1'b0;
        s_axis_tlast <= 0;
    end
    else if(cycle == 8) begin
        m_axis_tready <= 1;
        s_axis_tvalid <= 1'b1;
        s_axis_tlast <= 0;
    end
    else if(cycle == 9) begin
        s_axis_tlast <= 1'b1;
    end
    else if (cycle == 10) begin
        s_axis_tlast <= 1'b0;
        s_axis_tdata <= 7;
    end
    else if (cycle == 14) begin
        $finish;
    end
end

always @(*) begin
    if(m_axis_tdata==26'd6) begin
        $display("@@@Error: A frame with data=6 which should be dropped is now read!");
        $finish;
    end
end

axis_fifo 
#(
    .ADDR_WIDTH(ADDR_WIDTH),
    .DATA_WIDTH(DATA_WIDTH),
    .KEEP_ENABLE(KEEP_ENABLE),
    .KEEP_WIDTH(KEEP_WIDTH),
    .LAST_ENABLE(LAST_ENABLE),
    .ID_ENABLE(ID_ENABLE),
    .ID_WIDTH(ID_WIDTH),
    .DEST_ENABLE(DEST_ENABLE),
    .DEST_WIDTH(DEST_WIDTH),
    .USER_ENABLE(USER_ENABLE),
    .USER_WIDTH(USER_WIDTH),
    .FRAME_FIFO(FRAME_FIFO),
    .USER_BAD_FRAME_VALUE(USER_BAD_FRAME_VALUE),
    .USER_BAD_FRAME_MASK(USER_BAD_FRAME_MASK),
    .DROP_BAD_FRAME(DROP_BAD_FRAME),
    .DROP_WHEN_FULL(DROP_WHEN_FULL)
)
UUT (
    .clk(clk),
    .rst(rst),
    // AXI input
    .s_axis_tdata(s_axis_tdata),
    .s_axis_tkeep(s_axis_tkeep),
    .s_axis_tvalid(s_axis_tvalid),
    .s_axis_tready(s_axis_tready),
    .s_axis_tlast(s_axis_tlast),
    .s_axis_tid(s_axis_tid),
    .s_axis_tdest(s_axis_tdest),
    .s_axis_tuser(s_axis_tuser),
    // AXI output
    .m_axis_tdata(m_axis_tdata),
    .m_axis_tkeep(m_axis_tkeep),
    .m_axis_tvalid(m_axis_tvalid),
    .m_axis_tready(m_axis_tready),
    .m_axis_tlast(m_axis_tlast),
    .m_axis_tid(m_axis_tid),
    .m_axis_tdest(m_axis_tdest),
    .m_axis_tuser(m_axis_tuser),
    // Status
    .status_overflow(),
    .status_bad_frame(),
    .status_good_frame()
);

endmodule
