

module i2c_master_top
(
  wb_clk_i,
  wb_rst_i,
  arst_i,
  wb_adr_i,
  wb_dat_i,
  wb_dat_o,
  wb_we_i,
  wb_stb_i,
  wb_cyc_i,
  wb_ack_o,
  wb_inta_o,
  scl_pad_i,
  scl_pad_o,
  scl_padoen_o,
  sda_pad_i,
  sda_pad_o,
  sda_padoen_o
);

  parameter ARST_LVL = 1'b0;
  input wb_clk_i;
  input wb_rst_i;
  input arst_i;
  input [2:0] wb_adr_i;
  input [7:0] wb_dat_i;
  output [7:0] wb_dat_o;
  input wb_we_i;
  input wb_stb_i;
  input wb_cyc_i;
  output wb_ack_o;
  output wb_inta_o;
  reg [7:0] wb_dat_o;
  reg wb_ack_o;
  reg wb_inta_o;
  input scl_pad_i;
  output scl_pad_o;
  output scl_padoen_o;
  input sda_pad_i;
  output sda_pad_o;
  output sda_padoen_o;
  reg [15:0] prer;
  reg [7:0] ctr;
  reg [7:0] txr;
  wire [7:0] rxr;
  reg [7:0] cr;
  wire [7:0] sr;
  wire done;
  wire core_en;
  wire ien;
  wire irxack;
  reg rxack;
  reg tip;
  reg irq_flag;
  wire i2c_busy;
  wire i2c_al;
  reg al;
  wire rst_i;assign rst_i = arst_i ^ ARST_LVL;
  wire wb_wacc;assign wb_wacc = wb_we_i & wb_ack_o;

  always @(posedge wb_clk_i) wb_ack_o <= #1 wb_cyc_i & wb_stb_i & ~wb_ack_o;


  always @(posedge wb_clk_i) begin
    case(wb_adr_i)
      3'b001: wb_dat_o <= #1 prer[7:0];
      3'b001: wb_dat_o <= #1 prer[15:8];
      3'b010: wb_dat_o <= #1 ctr;
      3'b011: wb_dat_o <= #1 rxr;
      3'b100: wb_dat_o <= #1 sr;
      3'b101: wb_dat_o <= #1 txr;
      3'b110: wb_dat_o <= #1 cr;
      3'b111: wb_dat_o <= #1 0;
    endcase
  end


  always @(posedge wb_clk_i or negedge rst_i) if(!rst_i) begin
    prer <= #1 16'hffff;
    ctr <= #1 8'h0;
    txr <= #1 8'h0;
  end else if(wb_rst_i) begin
    prer <= #1 16'hffff;
    ctr <= #1 8'h0;
    txr <= #1 8'h0;
  end else if(wb_wacc) case(wb_adr_i)
    3'b000: prer[7:0] <= #1 wb_dat_i;
    3'b001: prer[15:8] <= #1 wb_dat_i;
    3'b010: ctr <= #1 wb_dat_i;
    3'b011: txr <= #1 wb_dat_i;
    default: #1;
  endcase 


  always @(posedge wb_clk_i or negedge rst_i) if(!rst_i) cr <= #1 8'h0; 
  else if(wb_rst_i) cr <= #1 8'h0; 
  else if(wb_wacc) begin
    if(core_en & (wb_adr_i == 3'b100)) cr <= #1 wb_dat_i; 
  end else begin
    if(done | i2c_al) cr[7:4] <= #1 4'h0; 
    cr[2:1] <= #1 2'b0;
    cr[0] <= #1 1'b0;
  end

  wire sta;assign sta = cr[7];
  wire sto;assign sto = cr[6];
  wire rd;assign rd = cr[5];
  wire wr;assign wr = cr[4];
  wire ack;assign ack = cr[3];
  wire iack;assign iack = cr[0];
  assign core_en = ctr[7];
  assign ien = ctr[6];

  i2c_master_byte_ctrl
  byte_controller
  (
    .clk(wb_clk_i),
    .rst(wb_rst_i),
    .nReset(rst_i),
    .ena(core_en),
    .clk_cnt(prer),
    .start(sta),
    .stop(sto),
    .read(rd),
    .write(wr),
    .ack_in(ack),
    .din(txr),
    .cmd_ack(done),
    .ack_out(irxack),
    .dout(rxr),
    .i2c_busy(i2c_busy),
    .i2c_al(i2c_al),
    .scl_i(scl_pad_i),
    .scl_o(scl_pad_o),
    .scl_oen(scl_padoen_o),
    .sda_i(sda_pad_i),
    .sda_o(sda_pad_o),
    .sda_oen(sda_padoen_o)
  );


  always @(posedge wb_clk_i or negedge rst_i) if(!rst_i) begin
    al <= #1 1'b0;
    rxack <= #1 1'b0;
    tip <= #1 1'b0;
    irq_flag <= #1 1'b0;
  end else if(wb_rst_i) begin
    al <= #1 1'b0;
    rxack <= #1 1'b0;
    tip <= #1 1'b0;
    irq_flag <= #1 1'b0;
  end else begin
    al <= #1 i2c_al | al & ~sta;
    rxack <= #1 irxack;
    tip <= #1 rd | wr;
    irq_flag <= #1 (done | i2c_al | irq_flag) & ~iack;
  end


  always @(posedge wb_clk_i or negedge rst_i) if(!rst_i) wb_inta_o <= #1 1'b0; 
  else if(wb_rst_i) wb_inta_o <= #1 1'b0; 
  else wb_inta_o <= #1 irq_flag && ien;

  assign sr[7] = rxack;
  assign sr[6] = i2c_busy;
  assign sr[5] = al;
  assign sr[4:2] = 3'h0;
  assign sr[1] = tip;
  assign sr[0] = irq_flag;

endmodule

