`timescale 1ns / 1ps

module axis_fifo_wrapper
(
    input  wire                   async_rst,
    input  wire                   clk,

    /*
     * AXI input
     */
    input  wire [7:0]             input_axis_tdata,
    input  wire                   input_axis_tvalid,
    output wire                   input_axis_tready,
    input  wire                   input_axis_tlast,
    input  wire                   input_axis_tuser,
    
    /*
     * AXI output
     */
    output wire [7:0]             output_axis_tdata,
    output wire                   output_axis_tvalid,
    input  wire                   output_axis_tready,
    output wire                   output_axis_tlast,
    output wire                   output_axis_tuser
);

wire [7:0]             reg_axis_tdata;
wire                   reg_axis_tvalid;
wire                   reg_axis_tready;
wire                   reg_axis_tlast;
wire                   reg_axis_tuser;

axis_register #(
    .DATA_WIDTH(8)
)
axis_reg_inst (
    .clk(clk),
    .rst(async_rst),
    .s_axis_tdata(input_axis_tdata),
    .s_axis_tvalid(input_axis_tvalid),
    .s_axis_tready(input_axis_tready),
    .s_axis_tlast(input_axis_tlast),
    .s_axis_tuser(input_axis_tuser),
    .m_axis_tdata(reg_axis_tdata),
    .m_axis_tvalid(reg_axis_tvalid),
    .m_axis_tready(reg_axis_tready),
    .m_axis_tlast(reg_axis_tlast),
    .m_axis_tuser(reg_axis_tuser)
);

axis_async_fifo #(
    .ADDR_WIDTH(5),
    .DATA_WIDTH(8)
)
UUT (
    // Common reset
    .async_rst(async_rst),
    // AXI input
    .input_clk(clk),
    .input_axis_tdata(reg_axis_tdata),
    .input_axis_tvalid(reg_axis_tvalid),
    .input_axis_tready(reg_axis_tready),
    .input_axis_tlast(reg_axis_tlast),
    .input_axis_tuser(reg_axis_tuser),
    // AXI output
    .output_clk(clk),
    .output_axis_tdata(output_axis_tdata),
    .output_axis_tvalid(output_axis_tvalid),
    .output_axis_tready(output_axis_tready),
    .output_axis_tlast(output_axis_tlast),
    .output_axis_tuser(output_axis_tuser)
);

endmodule
